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
import os
import pathlib
import re
import stat
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

try:  # inside the package
    from foundry import evidence as fe
except ImportError:  # inside an exported bundle
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    import foundry_evidence as fe  # type: ignore

FORBIDDEN_BODY_KEYS = {"prompt", "response", "content", "raw", "email", "password", "secret"}
MAX_BUNDLE_BYTES = 2_000_000
MAX_MANIFEST_ENTRIES = 1000


def object_fields(value, strings=(), objects=(), arrays=()):
    if not isinstance(value, dict):
        raise ValueError("expected JSON object")
    for names, kind in ((strings, str), (objects, dict), (arrays, list)):
        if any(not isinstance(value.get(k), kind) for k in names):
            raise ValueError("invalid object fields")
    return value


def integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError("expected nonnegative integer")
    return value


def validate_packet_display(packet):
    if "risk_tier" in packet and packet["risk_tier"] not in ("T1", "T2", "T3", "T4"):
        raise ValueError("invalid packet risk tier")
    for value in packet["pillars"].values():
        if integer(value) > 10000:
            raise ValueError("invalid pillar coverage")


def _parts(rel: str) -> list[str]:
    if (not isinstance(rel, str) or not rel or len(rel) > 4096
            or "\\" in rel or ":" in rel or "\0" in rel
            or any(p in ("", ".", "..") for p in rel.split("/"))):
        raise ValueError("unsafe bundle path")
    return rel.split("/")


def validate_manifest(manifest: object) -> dict:
    if not isinstance(manifest, dict) or not 0 < len(manifest) <= MAX_MANIFEST_ENTRIES:
        raise ValueError("manifest must be a nonempty bounded object")
    for rel, digest in manifest.items():
        _parts(rel)
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("manifest requires SHA-256 digests")
    return manifest


class _BundleReader:
    def __init__(self, root: pathlib.Path):
        if root.is_symlink():
            raise ValueError("bundle directory must not be a symlink")
        self.root = root.resolve(strict=True)
        self.remaining = MAX_BUNDLE_BYTES

    def path(self, rel: str, directory: bool = False) -> tuple[pathlib.Path, os.stat_result]:
        parts = _parts(rel)
        target = self.root
        for i, part in enumerate(parts):
            target = target / part
            info = target.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise ValueError("bundle paths must not contain symlinks")
            is_dir = directory or i < len(parts) - 1
            if not (stat.S_ISDIR(info.st_mode) if is_dir else stat.S_ISREG(info.st_mode)):
                raise ValueError("bundle paths must be directories or regular files as appropriate")
        if not target.resolve(strict=True).is_relative_to(self.root):
            raise ValueError("bundle path escapes its directory")
        return target, info

    def bytes(self, rel: str) -> bytes:
        target, expected = self.path(rel)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        with os.fdopen(os.open(target, flags), "rb") as f:
            actual = os.fstat(f.fileno())
            if (not stat.S_ISREG(actual.st_mode)
                    or (actual.st_dev, actual.st_ino) != (expected.st_dev, expected.st_ino)):
                raise ValueError("bundle file changed during validation")
            if actual.st_size > self.remaining:
                raise ValueError("bundle exceeds total byte limit")
            data = f.read(self.remaining + 1)
        if len(data) > self.remaining:
            raise ValueError("bundle exceeds total byte limit")
        self.remaining -= len(data)
        return data

    def text(self, rel: str) -> str:
        return self.bytes(rel).decode("utf-8")


def verify(d: pathlib.Path) -> dict:
    try:
        return _verify(_BundleReader(d))
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as e:
        return {"ok": False, "checks": [{"name": "structure", "ok": False, "detail": str(e)}]}


def _verify(reader: _BundleReader) -> dict:
    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    manifest = validate_manifest(json.loads(reader.text("manifest.json")))
    bad = [rel for rel, dg in manifest.items()
           if hashlib.sha256(reader.bytes("artifacts/" + rel)).hexdigest() != dg]
    add("manifest", not bad, f"{len(manifest)} artifacts match their digests" if not bad else f"digest mismatch: {bad}")

    keys = {}
    key_dir, _ = reader.path("keys", directory=True)
    for p in sorted(key_dir.glob("*.pub.hex")):
        pk = Ed25519PublicKey.from_public_bytes(bytes.fromhex(reader.text("keys/" + p.name).strip()))
        keys[fe.key_id(pk)] = pk

    env = object_fields(json.loads(reader.text("statement.dsse.json")),
                        strings=("payload", "payloadType"), arrays=("signatures",))
    for signature in env["signatures"]:
        object_fields(signature, strings=("keyid", "sig"))
    try:
        st = fe.dsse_verify(env, keys, threshold=2)
        subj = {s["name"]: s["digest"]["sha256"] for s in st["subject"]}
        if subj != manifest:
            add("statement", False, "signed subjects do not match manifest")
        else:
            add("statement", True, f"DSSE 2-of-{len(env['signatures'])} signatures valid")
    except Exception as e:  # noqa: BLE001
        add("statement", False, str(e))

    receipts = [json.loads(l) for l in reader.text("receipts.ndjson").splitlines() if l.strip()]
    if not receipts:
        raise ValueError("empty receipt log")
    for r in receipts:
        object_fields(r, strings=("type", "key_id", "prev", "sig", "ts_ns"), objects=("body",))
        integer(r.get("counter"), 1)
        if not re.fullmatch(r"[0-9]{1,30}", r["ts_ns"]):
            raise ValueError("invalid receipt timestamp")
        if "request_id" in r["body"]:
            object_fields(r["body"], strings=("request_id",))
        for k in ("approvers", "signers", "parent_scope", "child_scope"):
            if k in r["body"] and (not isinstance(r["body"][k], list) or any(not isinstance(s, str) for s in r["body"][k])):
                raise ValueError("invalid receipt body array")
        if r["type"] == "policy_approval":
            object_fields(r["body"], arrays=("approvers",))
    errs = fe.verify_chain(receipts, keys)
    leaks = [r["counter"] for r in receipts if FORBIDDEN_BODY_KEYS & set(r.get("body", {}).keys())]
    add("receipts", not errs, f"{len(receipts)} receipts signed, chained, counters contiguous" if not errs else "; ".join(errs[:5]))
    add("non-egress", not leaks, "receipt bodies hold commitments and digests only" if not leaks else f"content-like fields in receipts {leaks}")

    cp = object_fields(json.loads(reader.text("checkpoint.json")),
                       strings=("log", "root", "ts_ns", "witness_keyid", "witness_sig"))
    integer(cp.get("size"))
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

    inc = object_fields(json.loads(reader.text("inclusion_bundle_signed.json")), arrays=("proof",))
    integer(inc.get("index"))
    integer(inc.get("size"), 1)
    if any(not isinstance(p, str) or not re.fullmatch(r"[0-9a-f]{64}", p) for p in inc["proof"]):
        raise ValueError("invalid inclusion proof")
    try:
        br = receipts[inc["index"]]
        ok = (inc["size"] == cp["size"] and br["type"] == "bundle_signed"
              and fe.verify_inclusion(leaves[inc["index"]], inc["index"], inc["size"], inc["proof"], cp["root"])
              and br["body"]["envelope_sha256"] == hashlib.sha256(fe.jcs(env)).hexdigest())
    except (IndexError, KeyError):
        ok = False
    add("inclusion", ok, "bundle_signed receipt proven in log and bound to this envelope" if ok else "inclusion proof or envelope binding failed")

    try:
        packet = object_fields(json.loads(reader.text("underwriting_packet.json")),
                               strings=("tenant", "receipt_log_root"), objects=("period", "pillars", "metrics"),
                               arrays=("system_inventory", "incidents", "limitations"))
        object_fields(packet["period"], strings=("start", "end"))
        validate_packet_display(packet)
        for k in ("gate_coverage_bp", "denial_rate_bp", "hitl_override_rate_bp", "attestation_gap_count", "median_review_latency_s"):
            integer(packet["metrics"].get(k))
        for k in ("data_privacy", "security", "safety", "reliability", "accountability", "society"):
            integer(packet["pillars"].get(k))
        if not packet["limitations"] or any(not isinstance(s, str) for s in packet["limitations"]):
            raise ValueError("invalid packet limitations")
        commitments = [(i, r) for i, r in enumerate(receipts) if r["type"] == "underwriting_packet"]
        packet_ok = (ok and not errs and root_ok and wit_ok and len(commitments) == 1
                     and commitments[0][0] > inc["index"]
                     and commitments[0][1]["body"].get("packet_sha256") == hashlib.sha256(fe.jcs(packet)).hexdigest())
    except ValueError as e:
        if "total byte limit" in str(e):
            raise
        packet_ok = False
    except (OSError, KeyError, TypeError):
        packet_ok = False
    add("underwriting-packet", packet_ok, "Packet matches its signed, checkpointed receipt after bundle signing" if packet_ok else "Packet missing, malformed, or not bound to the signed receipt log")

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
