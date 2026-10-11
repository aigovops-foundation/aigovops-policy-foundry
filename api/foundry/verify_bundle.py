#!/usr/bin/env python3
"""
verify_bundle.py -- offline verifier shipped inside every Foundry bundle.

    python3 verify_bundle.py <bundle-dir>

Exit 0 = every check passed. Any failure exits non-zero and names the check. No network calls.
The same checks run in the browser (web/src/lib/verify.ts) against bundle.json.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

try:  # inside the package
    from foundry import evidence as fe
except ImportError:  # inside an exported bundle
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    import foundry_evidence as fe  # type: ignore

FORBIDDEN_BODY_KEYS = {"prompt", "response", "content", "raw", "email", "password", "secret"}


def verify(d: pathlib.Path) -> dict:
    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    keys = {}
    for p in sorted((d / "keys").glob("*.pub.hex")):
        pk = Ed25519PublicKey.from_public_bytes(bytes.fromhex(p.read_text().strip()))
        keys[fe.key_id(pk)] = pk

    manifest = json.loads((d / "manifest.json").read_text())
    bad = [rel for rel, dg in manifest.items()
           if not (d / "artifacts" / rel).exists()
           or hashlib.sha256((d / "artifacts" / rel).read_bytes()).hexdigest() != dg]
    add("manifest", not bad, f"{len(manifest)} artifacts match their digests" if not bad else f"digest mismatch: {bad}")

    env = json.loads((d / "statement.dsse.json").read_text())
    try:
        st = fe.dsse_verify(env, keys, threshold=2)
        subj = {s["name"]: s["digest"]["sha256"] for s in st["subject"]}
        if subj != manifest:
            add("statement", False, "signed subjects do not match manifest")
        else:
            add("statement", True, f"DSSE 2-of-{len(env['signatures'])} signatures valid")
    except Exception as e:  # noqa: BLE001
        add("statement", False, str(e))

    receipts = [json.loads(l) for l in (d / "receipts.ndjson").read_text().splitlines() if l.strip()]
    errs = fe.verify_chain(receipts, keys)
    leaks = [r["counter"] for r in receipts if FORBIDDEN_BODY_KEYS & set(r.get("body", {}).keys())]
    add("receipts", not errs, f"{len(receipts)} receipts signed, chained, counters contiguous" if not errs else "; ".join(errs[:5]))
    add("non-egress", not leaks, "receipt bodies hold commitments and digests only" if not leaks else f"content-like fields in receipts {leaks}")

    cp = json.loads((d / "checkpoint.json").read_text())
    leaves = [fe.jcs(r) for r in receipts]
    root_ok = fe.merkle_root(leaves) == cp["root"] and cp["size"] == len(leaves)
    sth = {k: cp[k] for k in ("log", "size", "root", "ts_ns")}
    try:
        keys[cp["witness_keyid"]].verify(fe.unb64(cp["witness_sig"]), fe.jcs(sth))
        wit_ok = True
    except Exception:  # noqa: BLE001
        wit_ok = False
    add("checkpoint", root_ok and wit_ok,
        f"witness-signed Merkle root {cp['root'][:16]}" if root_ok and wit_ok
        else ("Merkle root/size mismatch" if not root_ok else "witness signature invalid"))

    inc = json.loads((d / "inclusion_bundle_signed.json").read_text())
    try:
        br = receipts[inc["index"]]
        ok = (br["type"] == "bundle_signed"
              and fe.verify_inclusion(leaves[inc["index"]], inc["index"], inc["size"], inc["proof"], cp["root"])
              and br["body"]["envelope_sha256"] == hashlib.sha256(fe.jcs(env)).hexdigest())
    except (IndexError, KeyError):
        ok = False
    add("inclusion", ok, "bundle_signed receipt proven in log and bound to this envelope" if ok else "inclusion proof or envelope binding failed")

    return {"ok": all(c["ok"] for c in checks), "checks": checks}


def main(argv: list[str]) -> int:
    res = verify(pathlib.Path(argv[1] if len(argv) > 1 else "."))
    for c in res["checks"]:
        print(f"  {'ok  ' if c['ok'] else 'FAIL'} {c['name']}: {c['detail']}")
    print("foundry-verify:", "OK" if res["ok"] else "FAILED")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))


def cli() -> None:
    sys.exit(main(sys.argv))
