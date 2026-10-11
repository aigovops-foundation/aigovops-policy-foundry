import hashlib, json, pathlib, shutil, subprocess, sys
import pytest
from foundry import evidence as fe
from foundry import pipeline
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def test_jcs_sorts_keys_and_is_compact():
    assert fe.jcs({"b": 1, "a": [True, None, "x"]}) == b'{"a":[true,null,"x"],"b":1}'


def test_jcs_utf16_key_order():
    # RFC 8785 sorts by UTF-16 code units: U+20AC (euro) < U+1F600 surrogate pair (D83D...)
    assert fe.jcs({"\U0001F600": 1, "\u20ac": 2}).decode() == '{"\u20ac":2,"\U0001F600":1}'


@pytest.mark.parametrize("bad", [1.5, {"x": 0.1}, 2**60])
def test_jcs_rejects_floats_and_unsafe_ints(bad):
    with pytest.raises(fe.CanonicalizationError):
        fe.jcs(bad)


def test_commitment_is_keyed_and_tenant_scoped():
    root = b"r" * 32
    a = fe.commit(fe.derive_commitment_key(root, "t1", "identity"), b"u-chen")
    b = fe.commit(fe.derive_commitment_key(root, "t2", "identity"), b"u-chen")
    assert a != b and hashlib.sha256(b"u-chen").hexdigest() not in a


def _chain(n=5):
    k = Ed25519PrivateKey.generate()
    c = fe.ReceiptChain(signer=k, arbiter_id="a", tenant_id="t")
    for i in range(n):
        c.emit("permit", {"i": i}, now_ns=1_700_000_000_000_000_000 + i)
    return c, {fe.key_id(k.public_key()): k.public_key()}


def test_chain_verifies():
    c, keys = _chain()
    assert fe.verify_chain(c.receipts, keys) == []


def test_chain_detects_edit():
    c, keys = _chain()
    c.receipts[2]["body"]["i"] = 99
    assert any("#2" in e for e in fe.verify_chain(c.receipts, keys))


def test_chain_detects_drop():
    c, keys = _chain()
    del c.receipts[2]
    errs = fe.verify_chain(c.receipts, keys)
    assert any("chain break" in e for e in errs) and any("counter gap" in e for e in errs)


def test_chain_rejects_unknown_key():
    c, _ = _chain()
    other = Ed25519PrivateKey.generate().public_key()
    assert fe.verify_chain(c.receipts, {fe.key_id(other): other})


@pytest.mark.parametrize("n", range(1, 33))
def test_inclusion_proofs_all_sizes(n):
    leaves = [f"leaf{i}".encode() for i in range(n)]
    root = fe.merkle_root(leaves)
    for i in range(n):
        assert fe.verify_inclusion(leaves[i], i, n, fe.inclusion_proof(leaves, i), root)
    if n > 1:
        assert not fe.verify_inclusion(b"forged", 0, n, fe.inclusion_proof(leaves, 0), root)


def test_dsse_threshold():
    k1, k2 = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    keys = {fe.key_id(k.public_key()): k.public_key() for k in (k1, k2)}
    st = {"_type": "https://in-toto.io/Statement/v1", "subject": [], "predicateType": "x", "predicate": {}}
    assert fe.dsse_verify(fe.dsse_sign(st, [k1, k2]), keys, threshold=2) == st
    with pytest.raises(ValueError):
        fe.dsse_verify(fe.dsse_sign(st, [k1]), keys, threshold=2)


def test_dsse_kms_size_guard():
    k = Ed25519PrivateKey.generate()
    with pytest.raises(ValueError, match="4096"):
        fe.dsse_sign({"blob": "x" * 5000}, [k])


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    out = tmp_path_factory.mktemp("b") / "bundle"
    pipeline.run(out)
    return out


def _verify(d):
    return subprocess.run([sys.executable, "verify_bundle.py", "."], cwd=d, capture_output=True, text=True)


def test_bundle_verifies(bundle):
    r = _verify(bundle)
    assert r.returncode == 0, r.stdout


def test_mutation_kills_all_rules(bundle):
    rep = json.loads((bundle / "artifacts/reports/verifier.json").read_text())
    assert rep["mutation_score_bp"] == 10000 and rep["verdict"] == "pass"


@pytest.mark.parametrize("tamper", ["policy", "receipt", "drop_sig", "checkpoint"])
def test_bundle_tamper_detected(bundle, tmp_path, tamper):
    d = tmp_path / "t"
    shutil.copytree(bundle, d)
    if tamper == "policy":
        p = d / "artifacts/policy/ai_code_change.rego"
        p.write_text(p.read_text().replace('"ot-l2", ', ""))
    elif tamper == "receipt":
        lines = (d / "receipts.ndjson").read_text().splitlines()
        r = json.loads(lines[5]); r["body"]["agent"] = "attacker"; lines[5] = json.dumps(r)
        (d / "receipts.ndjson").write_text("\n".join(lines) + "\n")
    elif tamper == "drop_sig":
        e = json.loads((d / "statement.dsse.json").read_text()); e["signatures"] = e["signatures"][:1]
        (d / "statement.dsse.json").write_text(json.dumps(e))
    elif tamper == "checkpoint":
        c = json.loads((d / "checkpoint.json").read_text()); c["size"] -= 1
        (d / "checkpoint.json").write_text(json.dumps(c))
    r = _verify(d)
    assert r.returncode != 0 and "FAIL" in r.stdout
