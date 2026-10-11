"""
foundry_evidence.py -- reference evidence primitives for the Governed Policy Foundry.

Scope (read before relying on this):
  * Illustrative reference code for the blueprint, not a registered OVERT Protocol Profile
    and not a substitute for AiGovOps Beacon's signer/verifier.
  * Receipts use the JSON path that OVERT 1.0 Annex B anticipates for JSON profiles:
    RFC 8785 (JCS) canonical bytes + Ed25519. Protocol Profile 1.0's Base Envelope itself
    is deterministic CBOR; if the deployment registers against Profile 1.0, swap the encoder.
  * Floats are rejected (OVERT Annex B.3 prohibits IEEE-754 floats in envelopes).
  * Local Ed25519 keys stand in for AWS KMS ECC_NIST_EDWARDS25519 keys (ED25519_SHA_512, RAW).
    The production design adds a second ML-DSA (KMS ML_DSA_65) signature to every DSSE envelope.

Primitives:
  jcs()                    RFC 8785 canonical JSON for the float-free subset
  commit()                 HKDF-derived, tenant-scoped HMAC-SHA256 keyed commitment
  ReceiptChain             signed, hash-chained, monotonic-counter receipt log (NDJSON)
  merkle_root()/inclusion  RFC 6962-style Merkle tree (0x00 leaf / 0x01 node prefixes)
  dsse_sign()/dsse_verify  DSSE v1 envelope over an in-toto Statement (PAE signing)
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

# --------------------------------------------------------------------------- JCS


class CanonicalizationError(ValueError):
    pass


def _jcs_str(s: str) -> str:
    # json.dumps with ensure_ascii=False matches RFC 8785 string escaping for
    # the control/quote/backslash set; JCS requires lowercase \u00XX for controls.
    return json.dumps(s, ensure_ascii=False)


def _jcs(v: Any) -> str:
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, float):
        raise CanonicalizationError("floats are prohibited; use scaled integers or decimal strings")
    if isinstance(v, int):
        if abs(v) > 2**53 - 1:
            raise CanonicalizationError("integer outside I-JSON safe range; encode as string")
        return str(v)
    if isinstance(v, str):
        return _jcs_str(v)
    if isinstance(v, (list, tuple)):
        return "[" + ",".join(_jcs(x) for x in v) + "]"
    if isinstance(v, dict):
        for k in v:
            if not isinstance(k, str):
                raise CanonicalizationError("object keys must be strings")
        # RFC 8785: sort by UTF-16 code units
        keys = sorted(v.keys(), key=lambda k: k.encode("utf-16-be"))
        return "{" + ",".join(_jcs_str(k) + ":" + _jcs(v[k]) for k in keys) + "}"
    raise CanonicalizationError(f"unsupported type {type(v).__name__}")


def jcs(v: Any) -> bytes:
    return _jcs(v).encode("utf-8")


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ------------------------------------------------------------ keyed commitments


def derive_commitment_key(operator_root_secret: bytes, tenant_id: str, purpose: str) -> bytes:
    """HKDF-SHA256 tenant-scoped key (OVERT ATT-1.2 / §17.2 pattern). Never leaves operator KMS in prod."""
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=tenant_id.encode(),
        info=f"foundry/{purpose}/v1".encode(),
    ).derive(operator_root_secret)


def commit(key: bytes, content: bytes) -> str:
    """Keyed commitment: HMAC(key, SHA-256(content)). Only this crosses the trust boundary."""
    digest = hashlib.sha256(content).digest()
    return "hmac-sha256:" + hmac.new(key, digest, hashlib.sha256).hexdigest()


# --------------------------------------------------------------------- keys


def key_id(pub: Ed25519PublicKey) -> str:
    raw = pub.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return "ed25519:" + hashlib.sha256(raw).hexdigest()[:16]


def b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def unb64(s: str) -> bytes:
    return base64.b64decode(s.encode())


# ----------------------------------------------------------------- receipts

RECEIPT_TYPES = {
    # OVERT 1.0/1.1 named receipt families used by the Foundry
    "session_open", "session_close",            # SESS-1 / SESS-2
    "delegation",                                 # IDENT-1.2
    "permit", "denial",                           # PRO-1.4 / PRO-1.3, TOOL-1.3
    "escalation",                                 # TOOL-4.2 held pending human approval
    "review",                                     # HITL-2.2
    "policy_approval",                            # HITL-4.1 (+ HITL-4.3 SoD)
    "test_commitment",                            # Foundry extension: verifier test-first commitment
    "bundle_signed",                              # Beacon action verb bundle.signed
    "underwriting_packet",                        # Foundry extension
    "attestation_gap",                            # ATT-3.4
}


@dataclass
class ReceiptChain:
    signer: Ed25519PrivateKey
    arbiter_id: str
    tenant_id: str
    epoch_seconds: int = 300  # OVERT §18.1 recommended epoch
    counter: int = 0
    prev_hash: str = "0" * 64
    receipts: list[dict] = field(default_factory=list)

    def emit(self, rtype: str, body: dict, now_ns: int | None = None) -> dict:
        if rtype not in RECEIPT_TYPES:
            raise ValueError(f"unknown receipt type {rtype}")
        now_ns = now_ns if now_ns is not None else time.time_ns()
        self.counter += 1
        unsigned = {
            "schema": "foundry.receipt/v0.1",
            "type": rtype,
            "tenant": self.tenant_id,
            "arbiter_id": self.arbiter_id,
            "counter": self.counter,
            "ts_ns": str(now_ns),  # uint64 ns as string: avoids I-JSON overflow
            "epoch": now_ns // (self.epoch_seconds * 1_000_000_000),
            "prev": self.prev_hash,
            "key_id": key_id(self.signer.public_key()),
            "body": body,
        }
        canon = jcs(unsigned)
        sig = self.signer.sign(canon)
        receipt = dict(unsigned, sig=b64(sig))
        self.prev_hash = sha256_hex(canon)
        self.receipts.append(receipt)
        return receipt

    def ndjson(self) -> str:
        return "\n".join(json.dumps(r, sort_keys=True) for r in self.receipts) + "\n"


def verify_chain(receipts: list[dict], pubkeys: dict[str, Ed25519PublicKey]) -> list[str]:
    """Return list of failures (empty == OK). Fails closed on any anomaly."""
    errors: list[str] = []
    prev = "0" * 64
    expected_counter = 1
    for i, r in enumerate(receipts):
        r = dict(r)
        sig = r.pop("sig", None)
        if sig is None:
            errors.append(f"#{i}: missing signature")
            continue
        pk = pubkeys.get(r.get("key_id", ""))
        if pk is None:
            errors.append(f"#{i}: unknown key_id {r.get('key_id')}")
            continue
        try:
            canon = jcs(r)
            pk.verify(unb64(sig), canon)
        except Exception as e:  # noqa: BLE001
            errors.append(f"#{i}: signature/canonicalization failure ({type(e).__name__})")
            continue
        if r["prev"] != prev:
            errors.append(f"#{i}: chain break (prev mismatch)")
        if r["counter"] != expected_counter:
            errors.append(f"#{i}: counter gap (got {r['counter']}, want {expected_counter})")
        prev = sha256_hex(canon)
        expected_counter = r["counter"] + 1
    return errors


# -------------------------------------------------------------- Merkle (6962)


def _leaf(b: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + b).digest()


def _node(l: bytes, r: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + l + r).digest()


def _mth(leaves: list[bytes]) -> bytes:
    n = len(leaves)
    if n == 0:
        return hashlib.sha256(b"").digest()
    if n == 1:
        return _leaf(leaves[0])
    k = 1
    while k * 2 < n:
        k *= 2
    return _node(_mth(leaves[:k]), _mth(leaves[k:]))


def merkle_root(entries: list[bytes]) -> str:
    return _mth(entries).hex()


def inclusion_proof(entries: list[bytes], index: int) -> list[str]:
    def path(m: int, d: list[bytes]) -> list[bytes]:
        n = len(d)
        if n == 1:
            return []
        k = 1
        while k * 2 < n:
            k *= 2
        if m < k:
            return path(m, d[:k]) + [_mth(d[k:])]
        return path(m - k, d[k:]) + [_mth(d[:k])]

    return [h.hex() for h in path(index, entries)]


def verify_inclusion(entry: bytes, index: int, size: int, proof: list[str], root: str) -> bool:
    """RFC 9162 §2.1.3.2 verification algorithm."""
    if index >= size:
        return False
    fn, sn = index, size - 1
    r = _leaf(entry)
    for p_hex in proof:
        p = bytes.fromhex(p_hex)
        if sn == 0:
            return False
        if fn & 1 or fn == sn:
            r = _node(p, r)
            if not fn & 1:
                while fn and not fn & 1:
                    fn >>= 1
                    sn >>= 1
        else:
            r = _node(r, p)
        fn >>= 1
        sn >>= 1
    return sn == 0 and r.hex() == root


# -------------------------------------------------------------------- DSSE


def pae(payload_type: str, payload: bytes) -> bytes:
    t = payload_type.encode()
    return b"DSSEv1 %d %s %d %s" % (len(t), t, len(payload), payload)


KMS_RAW_LIMIT = 4096  # AWS KMS Sign RAW message cap


def dsse_sign(statement: dict, signers: list[Ed25519PrivateKey]) -> dict:
    payload_type = "application/vnd.in-toto+json"
    payload = jcs(statement)
    msg = pae(payload_type, payload)
    if len(msg) > KMS_RAW_LIMIT:
        raise ValueError(
            f"PAE is {len(msg)} bytes; keep in-toto statements digest-only so KMS RAW signing (<=4096) works"
        )
    return {
        "payloadType": payload_type,
        "payload": b64(payload),
        "signatures": [{"keyid": key_id(s.public_key()), "sig": b64(s.sign(msg))} for s in signers],
    }


def dsse_verify(env: dict, pubkeys: dict[str, Ed25519PublicKey], threshold: int = 1) -> dict:
    payload = unb64(env["payload"])
    msg = pae(env["payloadType"], payload)
    good = set()
    for s in env["signatures"]:
        pk = pubkeys.get(s["keyid"])
        if pk is None:
            continue
        try:
            pk.verify(unb64(s["sig"]), msg)
            good.add(s["keyid"])
        except Exception:  # noqa: BLE001
            pass
    if len(good) < threshold:
        raise ValueError(f"DSSE threshold not met ({len(good)}/{threshold})")
    return json.loads(payload)
