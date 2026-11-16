"""Tool failures are inconclusive, never passing acceptance or killed mutants."""
import json
import subprocess

import pytest

from foundry import pipeline


def completed(code=0, output='[{"name":"test_acceptance"}]'):
    return subprocess.CompletedProcess(["synthetic-opa"], code, stdout=output, stderr="")


@pytest.mark.parametrize("code,output", [
    (2, ""), (1, ""), (2, '[{"name":"test_acceptance"}]'), (0, ""), (0, " "),
    (0, "not json"), (0, "null"), (0, "{}"), (0, "[]"), (0, "[{}]"),
    (0, '[{"name":"test_skipped","skip":true}]'), (0, '[{"name":"test_bad","fail":"false"}]'),
    (0, '[{"name":"test_bad","error":{}}]'), (0, '[{"name":"test_bad","fail":true}]'),
])
def test_opa_test_rejects_execution_and_output_failures(monkeypatch, code, output):
    monkeypatch.setattr(pipeline, "_run_opa", lambda args: completed(code, output))
    with pytest.raises(pipeline.VerifierError):
        pipeline.opa_test([])


def test_opa_test_counts_only_executed_tests(monkeypatch):
    monkeypatch.setattr(pipeline, "_run_opa", lambda args: completed(output=json.dumps([
        {"name": "test_pass"}, {"name": "test_skip", "skip": True}])))
    assert pipeline.opa_test([]) == {"passed": 1, "failed": 0, "errors": 0, "failing_cases": []}


def test_mutant_nonzero_is_allowed_only_for_explicit_assertion_failure(monkeypatch):
    monkeypatch.setattr(pipeline, "_run_opa", lambda args: completed(2, '[{"name":"test_req","fail":true}]'))
    assert pipeline.opa_test([], mutation=True)["failed"] == 1
    with pytest.raises(pipeline.VerifierError):
        pipeline.opa_test([])


@pytest.mark.parametrize("code,output", [(2, "[]"), (2, '[{"name":"test_req"}]'),
                                      (1, '[{"name":"test_req","fail":true}]'),
                                      (2, '[{"name":"test_req","error":{"code":"eval_error"}}]')])
def test_mutant_tool_errors_are_not_kills(monkeypatch, code, output):
    monkeypatch.setattr(pipeline, "_run_opa", lambda args: completed(code, output))
    with pytest.raises(pipeline.VerifierError):
        pipeline.mutation_score(pipeline.EX / "policy/ai_code_change.rego", pipeline.EX / "tests/acceptance_test.rego")


@pytest.mark.parametrize("code,output", [(1, '{"coverage":100}'), (0, ""), (0, "[]"), (0, "null"),
                                      (0, "{}"), (0, '{"coverage":true}'), (0, '{"coverage":"100"}'),
                                      (0, '{"coverage":-1}'), (0, '{"coverage":101}'),
                                      (0, '{"coverage":NaN}'), (0, '{"coverage":Infinity}')])
def test_coverage_fails_closed(monkeypatch, code, output):
    monkeypatch.setattr(pipeline, "_run_opa", lambda args: completed(code, output))
    with pytest.raises(pipeline.VerifierError, match="coverage"):
        pipeline.opa_coverage([])


def test_coverage_valid_percentage(monkeypatch):
    monkeypatch.setattr(pipeline, "_run_opa", lambda args: completed(output='{"coverage":91.25}'))
    assert pipeline.opa_coverage([]) == 9125


@pytest.mark.parametrize("failure", [subprocess.TimeoutExpired("opa", 30), PermissionError("synthetic denied")])
def test_subprocess_errors_are_explicit_and_bounded(monkeypatch, failure):
    monkeypatch.setattr(pipeline.gt, "opa_bin", lambda: "synthetic-opa")

    def fake_run(args, **kwargs):
        assert kwargs["timeout"] == pipeline.OPA_TIMEOUT_SECONDS == 30
        assert kwargs["capture_output"] and kwargs["text"]
        raise failure

    monkeypatch.setattr(pipeline.subprocess, "run", fake_run)
    with pytest.raises(pipeline.VerifierError):
        pipeline._run_opa(["test"])


def test_successful_subprocess_is_also_bounded(monkeypatch):
    monkeypatch.setattr(pipeline.gt, "opa_bin", lambda: "synthetic-opa")

    def fake_run(args, **kwargs):
        assert args == ["synthetic-opa", "test"]
        assert kwargs["timeout"] == 30
        return completed()

    monkeypatch.setattr(pipeline.subprocess, "run", fake_run)
    assert pipeline._run_opa(["test"]).returncode == 0


def test_disappearing_opa_is_an_error_not_recorded_fallback(monkeypatch):
    monkeypatch.setattr(pipeline.gt, "opa_bin", lambda: None)
    with pytest.raises(pipeline.VerifierError, match="unavailable"):
        pipeline._run_opa(["test"])


def test_empty_mutation_set_is_inconclusive(tmp_path):
    policy = tmp_path / "empty.rego"
    policy.write_text("package empty\n")
    with pytest.raises(pipeline.VerifierError, match="zero mutants"):
        pipeline.mutation_score(policy, tmp_path / "tests.rego")


@pytest.mark.parametrize("stage", ["acceptance", "coverage", "mutation"])
def test_pipeline_does_not_sign_or_replay_when_opa_fails(tmp_path, monkeypatch, stage):
    monkeypatch.setattr(pipeline.gt, "opa_bin", lambda: "synthetic-opa")
    calls = []

    def fake_opa(args):
        calls.append(args)
        current = "acceptance" if len(calls) == 1 else "coverage" if "--coverage" in args else "mutation"
        if current == stage:
            return completed(2, "")
        if current == "coverage":
            return completed(output='{"coverage":100}')
        if current == "mutation":
            return completed(2, '[{"name":"test_req","fail":true}]')
        return completed()

    def must_not_sign(*args, **kwargs):
        pytest.fail("an inconclusive verifier must not produce a signed statement")

    monkeypatch.setattr(pipeline, "_run_opa", fake_opa)
    monkeypatch.setattr(pipeline.fe, "dsse_sign", must_not_sign)
    out = tmp_path / "out"
    with pytest.raises(pipeline.VerifierError):
        pipeline.run(out, engine="python")
    assert not (out / "statement.dsse.json").exists()
    assert not (out / "manifest.json").exists()


def test_zero_tests_cannot_pass_even_with_full_coverage_and_mutation(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline.gt, "opa_bin", lambda: "synthetic-opa")
    monkeypatch.setattr(pipeline, "opa_test", lambda paths: {"passed": 0, "failed": 0, "errors": 0, "failing_cases": []})
    monkeypatch.setattr(pipeline, "opa_coverage", lambda paths: 10000)
    monkeypatch.setattr(pipeline, "mutation_score", lambda *args: (7, 7))
    out = tmp_path / "out"
    with pytest.raises(pipeline.VerifierError, match="nonzero tests"):
        pipeline.run(out, engine="python")
    assert not (out / "statement.dsse.json").exists()


def test_cli_reports_inconclusive_without_writing_bundle_json(tmp_path, monkeypatch):
    out = tmp_path / "out"
    monkeypatch.setattr("sys.argv", ["foundry-demo", "--out", str(out), "--json"])

    def unavailable(*args):
        raise pipeline.VerifierError("OPA test command failed")

    monkeypatch.setattr(pipeline, "run", unavailable)
    with pytest.raises(SystemExit, match="foundry-demo: verifier inconclusive: OPA test command failed"):
        pipeline.cli()
    assert not (out / "bundle.json").exists()
