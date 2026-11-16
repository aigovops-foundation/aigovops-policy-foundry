"""E2E tests against the FastAPI app (in-process)."""
import copy
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)


def test_health_and_meta():
    assert c.get("/healthz").json()["ok"] is True
    m = c.get("/api/meta").json()
    assert m["devin_mode"] == "dry-run" and "Not an OVERT conformance claim" in m["assurance"]


def test_agents_manifest():
    a = c.get("/api/agents").json()
    assert set(a["agents"]) == {"manager", "policy_writer", "test_verifier", "compliance_auditor"}


@pytest.mark.parametrize("body,result", [
    ({"agent": "policy_writer", "action": "git.push", "target": "policy-src/branches/foundry/x"}, "allow"),
    ({"agent": "policy_writer", "action": "git.merge", "target": "policy-src/main"}, "escalate"),
    ({"agent": "policy_writer", "action": "network.connect", "target": "ot/l2/historian"}, "deny"),
    ({"agent": "manager", "action": "devin.session.create",
      "delegation": {"to": "policy_writer", "child_scope": ["git.read:policy-src"]}}, "deny"),
])
def test_gate(body, result):
    r = c.post("/api/gate/evaluate", json=body)
    assert r.status_code == 200 and r.json()["decision"]["result"] == result


def test_gate_rejects_unknown_fields():
    assert c.post("/api/gate/evaluate", json={"agent": "x", "action": "y", "evil": 1}).status_code == 422


def test_approvals():
    ok = c.post("/api/approvals/check", json={"requester": "u-patel", "signer": "u-okafor", "approvals": [
        {"subject": "u-alvarez", "groups": ["grp-ai-policy-owners"]},
        {"subject": "u-chen", "groups": ["grp-ai-governance-board"]}]}).json()
    assert ok["ok"] is True
    bad = c.post("/api/approvals/check", json={"requester": "u-alvarez", "signer": "u-okafor", "approvals": [
        {"subject": "u-alvarez", "groups": ["grp-ai-policy-owners"]}]}).json()
    assert not bad["ok"] and "requester-counted-as-approver" in bad["errors"]


@pytest.fixture(scope="module")
def run():
    r = c.post("/api/runs")
    assert r.status_code == 201
    return r.json()


def test_run_and_bundle_verify(run):
    assert run["verdict"] == "pass" and run["receipts"] == 20
    # the dashboard needs these straight from POST /api/runs
    assert {"tests", "coverage_bp", "mutation", "events"} <= set(run) and run["mutation"] == "7/7"
    b = c.get(f"/api/runs/{run['id']}/bundle.json").json()
    v = c.post("/api/verify", json=b).json()
    assert v["ok"], v
    t = copy.deepcopy(b)
    t["files"]["artifacts/policy/ai_code_change.rego"] += "\n# tampered\n"
    v2 = c.post("/api/verify", json=t).json()
    assert not v2["ok"] and not next(x for x in v2["checks"] if x["name"] == "manifest")["ok"]


def test_bundle_zip(run):
    r = c.get(f"/api/runs/{run['id']}/bundle.zip")
    assert r.status_code == 200 and r.content[:2] == b"PK"


def test_verify_rejects_path_traversal(run):
    b = c.get(f"/api/runs/{run['id']}/bundle.json").json()
    b["files"]["../../etc/x.json"] = "{}"
    assert c.post("/api/verify", json=b).status_code == 422


def test_verify_garbage_is_4xx_or_structured():
    r = c.post("/api/verify", json={"format": "foundry.bundle+json/v0.1", "files": {"manifest.json": "not json"}})
    assert r.status_code == 200 and r.json()["ok"] is False


@pytest.mark.parametrize("manifest", [[], {}, {"/synthetic/outside": "0" * 64}, {"../outside": "0" * 64},
                                     {"safe": "not-a-digest"}])
def test_invalid_manifest_rejected_before_materializing_files(monkeypatch, manifest):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid manifest must be rejected before filesystem access")

    monkeypatch.setattr("app.main.tempfile.TemporaryDirectory", forbidden)
    r = c.post("/api/verify", json={"format": "foundry.bundle+json/v0.1",
                                  "files": {"manifest.json": json.dumps(manifest)}})
    assert r.status_code == 200
    assert r.json()["ok"] is False and r.json()["checks"][0]["name"] == "structure"


def test_verify_byte_limit_counts_utf8_bytes():
    r = c.post("/api/verify", json={"format": "foundry.bundle+json/v0.1",
                                  "files": {"manifest.json": "é" * 1_000_001}})
    assert r.status_code == 413


def test_unknown_run_404():
    assert c.get("/api/runs/000000000000").status_code == 404
    assert c.get("/api/runs/../../x").status_code == 404


def test_inconclusive_verifier_returns_503_without_run_or_partial_bundle(monkeypatch, tmp_path):
    from app import main

    before = set(main.RUNS)

    def unavailable(out, engine):
        out.mkdir()
        (out / "partial").write_text("synthetic partial output")
        raise main.pipeline.VerifierError("OPA exceeded its execution deadline")

    monkeypatch.setattr(main, "WORK", tmp_path)
    monkeypatch.setattr(main.pipeline, "run", unavailable)
    response = c.post("/api/runs")
    assert response.status_code == 503
    assert response.json()["detail"] == "Verifier inconclusive: OPA exceeded its execution deadline"
    assert set(main.RUNS) == before
    assert list(tmp_path.iterdir()) == []


def test_token_required_when_configured(monkeypatch):
    monkeypatch.setenv("FOUNDRY_API_TOKEN", "s3cret")
    assert c.post("/api/runs").status_code == 401
    assert c.post("/api/runs", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_devin_preview_is_dry_run():
    r = c.post("/api/devin/preview", json={"role": "policy_writer"}).json()
    p = r["payload"]
    assert r["dry_run"] and p["bypass_approval"] is False and p["resumable"] is False
    assert "create_as_user_id" not in p and "{{" not in p["prompt"]


def test_cache_headers():
    assert c.get("/api/meta").headers["cache-control"] == "no-store"
    assert c.get("/healthz").headers["cache-control"] == "no-cache"
