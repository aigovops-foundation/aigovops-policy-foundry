"""The Python gate port must agree with OPA's golden output on every corpus case."""
import json
import pytest
from foundry import gate

A = gate.ASSETS / "parity"
CORPUS = json.loads((A / "corpus.json").read_text())
EXPECTED = json.loads((A / "expected.json").read_text())


@pytest.mark.parametrize("i", range(len(CORPUS["decisions"])))
def test_decision_parity(i):
    assert gate.decide_py(CORPUS["decisions"][i]) == EXPECTED["decisions"][i], CORPUS["decisions"][i]


@pytest.mark.parametrize("i", range(len(CORPUS["approvals"])))
def test_approval_parity(i):
    assert gate.approval_errors_py(CORPUS["approvals"][i]) == EXPECTED["approvals"][i]


@pytest.mark.skipif(not gate.opa_bin(), reason="OPA not installed")
def test_opa_engine_live_sample():
    for c, e in list(zip(CORPUS["decisions"], EXPECTED["decisions"]))[::97]:
        assert gate.decide(c, "opa")[0] == e


def test_glob_semantics():
    assert gate.glob_match("a/*", "a/b") and not gate.glob_match("a/*", "a/b/c")
    assert gate.glob_match("a/**", "a/b/c") and gate.glob_match("x:p/*", "x:p/q")
    assert not gate.glob_match("a.b", "aXb")
