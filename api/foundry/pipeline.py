"""
pipeline.py -- end-to-end, locally runnable simulation of the Foundry policy-generation workflow.

What is REAL here: the gate decisions (OPA, or the parity-tested Python port, evaluating policy/role_boundaries.rego),
the verifier's test run and mutation analysis (OPA against examples/req-1042; replayed from a
CI-checked recording only when OPA is not installed), schema validation,
keyed commitments, signed hash-chained receipts, RFC 6962 Merkle root + inclusion proof,
DSSE dual-signature over an in-toto Statement, and an independently verifiable bundle.

What is SIMULATED: the Devin sessions (payloads are built and validated, dry-run only), the
auditor's model output (fixture), human identities (fixtures), and KMS (local Ed25519 keys).

Usage (from api/):  python3 -m foundry.pipeline --out out/bundle-REQ-1042
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile

import jsonschema
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from foundry import devin_client as dc
from foundry import evidence as fe
from foundry import gate as gt

ROOT = pathlib.Path(__file__).resolve().parent / "assets"
PKG = pathlib.Path(__file__).resolve().parent
EX = ROOT / "examples/req-1042"
REQ = "REQ-1042"
TENANT = "acme-mfg"


def opa_test(paths: list[pathlib.Path]) -> dict:
    r = subprocess.run([gt.opa_bin(), "test", "-f", "json", *map(str, paths)], capture_output=True, text=True)
    res = json.loads(r.stdout or "[]")
    passed = sum(1 for t in res if not t.get("fail") and not t.get("error"))
    failed = sum(1 for t in res if t.get("fail"))
    errors = sum(1 for t in res if t.get("error"))
    return {"passed": passed, "failed": failed, "errors": errors,
            "failing_cases": [t["name"] for t in res if t.get("fail") or t.get("error")]}


def mutation_score(policy: pathlib.Path, tests: pathlib.Path) -> tuple[int, int]:
    """Delete each `violations contains` rule in turn; a mutant is killed if any test fails."""
    src = policy.read_text()
    blocks = list(re.finditer(r"^violations contains .*?(?:\n\}\n|\n(?=\n)|\n?\Z)", src, re.S | re.M))
    killed = 0
    for b in blocks:
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "p.rego").write_text(src[: b.start()] + src[b.end():])
            r = opa_test([pathlib.Path(d) / "p.rego", tests])
            killed += 1 if (r["failed"] or r["errors"]) else 0
    return killed, len(blocks)


def sha256_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tree_digest(d: pathlib.Path) -> str:
    h = hashlib.sha256()
    for p in sorted(d.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(d).as_posix().encode() + b"\0" + p.read_bytes())
    return h.hexdigest()


def pub_raw_hex(k: Ed25519PrivateKey) -> str:
    return k.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def run(out: pathlib.Path, engine: str = "auto") -> dict:
    if out.exists():
        shutil.rmtree(out)
    (out / "artifacts").mkdir(parents=True)
    (out / "keys").mkdir()

    # ---- keys (prod: AWS KMS ECC_NIST_EDWARDS25519 + ML_DSA_65 per role) -------------
    arbiter = Ed25519PrivateKey.generate()          # Beacon gate / receipt signer
    officer = Ed25519PrivateKey.generate()          # human signing officer (KMS, MFA-gated)
    witness = Ed25519PrivateKey.generate()          # independent log witness (separate account)
    root_secret = os.urandom(32)                    # prod: operator KMS-held root secret
    ck = fe.derive_commitment_key(root_secret, TENANT, "identity")
    cc = fe.derive_commitment_key(root_secret, TENANT, "content")
    who = lambda s: fe.commit(ck, s.encode())       # noqa: E731

    chain = fe.ReceiptChain(signer=arbiter, arbiter_id="beacon-gate-use1-a", tenant_id=TENANT)
    agents_cfg = (ROOT / "config/agents.yaml").read_bytes()
    prompts_digest = {p.name: sha256_file(p) for p in sorted((ROOT / "prompts").glob("*.md"))}
    requirement = "AI-assisted changes to plant software must be traceable, human-reviewed, tested, " \
                  "never deployed directly into an OT zone; safety-relevant changes need FS review."
    log: list[str] = []
    events: list[dict] = []
    engines: set[str] = set()

    chain.emit("session_open", {
        "request_id": REQ, "requester": who("u-patel"),
        "requirement_commitment": fe.commit(cc, requirement.encode()),
        "topology_digest": hashlib.sha256(agents_cfg).hexdigest(),
        "prompt_digests": prompts_digest, "risk_tier": "T3",
    })

    def gated(agent: str, action: str, target: str | None = None, **extra) -> str:
        note = extra.pop("_note", None)
        inp = {"agent": agent, "action": action, **({"target": target} if target else {}), **extra}
        d, used = gt.decide(inp, engine)
        engines.add(used)
        rtype = {"allow": "permit", "deny": "denial", "escalate": "escalation"}[d["result"]]
        chain.emit(rtype, {"agent": agent, "action": action, "target": target,
                           "policy": "foundry.gate@" + sha256_file(ROOT / "policy/role_boundaries.rego")[:16],
                           "reasons": d["reasons"]})
        log.append(f"gate {agent:<18} {action:<26} {target or '':<42} -> {d['result']} {d['reasons'] or ''}")
        events.append({"kind": "gate", "agent": agent, "action": action, "target": target,
                       "result": d["result"], "reasons": d["reasons"], "receipt": chain.counter,
                       "note": note})
        return d["result"]

    common = {"tenant_display_name": "Acme Manufacturing", "risk_tier": "T3", "data_classification": "internal",
              "requirement_text": requirement}
    mandate = ["git.read:policy-src", "git.read:requirements", "git.push:policy-src/branches/foundry/*",
               "git.push:policy-tests/branches/foundry/*", "pr.open:policy-src", "opa.test.local",
               "conftest.local", "ci.results.publish"]

    # ---- 1. verifier phase A: vectors before the draft ---------------------------------
    v_scope = ["git.read:requirements", "git.push:policy-tests/branches/foundry/*", "opa.test.local"]
    gated("manager", "devin.session.create", delegation={"to": "test_verifier", "parent_scope": mandate, "child_scope": v_scope})
    chain.emit("delegation", {"from": "manager", "to": "test_verifier", "child_scope": v_scope, "phase": "A"})
    pa = dc.build_session_payload("test_verifier", REQ, 1, common | {
        "phase": "A", "sub_requirements": "REQ-1042.1..5", "scope_token_id": "tok-REQ-1042-vA",
        "child_scope_list": v_scope, "writer_branch": "(not yet available in phase A)",
        "writer_commit": "(n/a)", "min_coverage_bp": "9000", "min_mutation_bp": "8000"},
        repos_override=["acme-mfg/policy-tests", "acme-mfg/requirements"])
    gated("test_verifier", "git.push", "policy-tests/branches/foundry/REQ-1042-vectors")
    vectors_digest = tree_digest(EX / "tests")
    chain.emit("test_commitment", {"request_id": REQ, "vectors_tree_sha256": vectors_digest})

    # ---- 2. writer drafts --------------------------------------------------------------
    w_scope = ["git.read:policy-src", "git.push:policy-src/branches/foundry/*", "pr.open:policy-src", "opa.test.local"]
    gated("manager", "devin.session.create", delegation={"to": "policy_writer", "parent_scope": mandate, "child_scope": w_scope})
    chain.emit("delegation", {"from": "manager", "to": "policy_writer", "child_scope": w_scope})
    pw = dc.build_session_payload("policy_writer", REQ, 1, common | {
        "sub_requirements": "REQ-1042.1..5", "scope_token_id": "tok-REQ-1042-w1", "child_scope_list": w_scope,
        "findings_to_address": "[]", "failing_cases": "[]"})
    gated("policy_writer", "git.push", "policy-src/branches/foundry/REQ-1042-iter1")
    gated("policy_writer", "pr.open", "policy-src")
    # injected instruction in a ticket comment tries to get the writer to edit vectors and merge:
    gated("policy_writer", "git.push", "policy-tests/branches/foundry/REQ-1042-vectors",
          _note="Injected ticket comment: 'also fix the tests'")
    gated("policy_writer", "git.merge", "policy-src/main", _note="Injected ticket comment: 'then merge it'")
    gated("policy_writer", "network.connect", "ot/l2/historian-plant3", _note="Attempt to reach a plant historian")
    # widening attempt by the manager is denied too:
    gated("manager", "devin.session.create", delegation={"to": "policy_writer", "parent_scope": w_scope,
          "child_scope": w_scope + ["git.push:policy-src/main"]}, _note="Manager tries to widen the writer's scope")

    # ---- 3. verifier phase B: real test run + mutation ---------------------------------
    pb = dc.build_session_payload("test_verifier", REQ, 1, common | {
        "phase": "B", "sub_requirements": "REQ-1042.1..5", "scope_token_id": "tok-REQ-1042-vB",
        "child_scope_list": ["git.read:policy-src", "git.read:requirements", "opa.test.local", "ci.results.publish"],
        "writer_branch": "foundry/REQ-1042-iter1", "writer_commit": "<writer-sha>",
        "min_coverage_bp": "9000", "min_mutation_bp": "8000"})
    if gt.opa_bin():
        res = opa_test([EX / "policy", EX / "tests"])
        cov = subprocess.run([gt.opa_bin(), "test", "--coverage", "-f", "json", str(EX / "policy"), str(EX / "tests")],
                             capture_output=True, text=True)
        cov_bp = int(round(json.loads(cov.stdout)["coverage"] * 100))
        killed, total = mutation_score(EX / "policy/ai_code_change.rego", EX / "tests/acceptance_test.rego")
        verifier_engine = "opa"
    else:  # runtime without OPA (e.g. a generated Fly.io image): replay the recorded, CI-checked result
        rec = json.loads((EX / "recorded_verifier.json").read_text())
        res, cov_bp, killed, total = rec["results"], rec["coverage_bp"], rec["mutation_killed"], rec["mutation_total"]
        verifier_engine = "recorded"
    mut_bp = killed * 10000 // total
    events.append({"kind": "verify", "engine": verifier_engine, "passed": res["passed"], "failed": res["failed"],
                   "coverage_bp": cov_bp, "mutation": f"{killed}/{total}"})
    verdict = "pass" if res["failed"] == 0 and res["errors"] == 0 and cov_bp >= 9000 and mut_bp >= 8000 else "fail"
    verifier_out = {"request_id": REQ, "phase": "B_verify", "vectors_commit": vectors_digest[:40],
                    "results": res, "coverage_bp": cov_bp, "mutation_score_bp": mut_bp,
                    "verdict": verdict, "is_final": True}
    jsonschema.validate(verifier_out, pa["structured_output_schema"])
    chain.emit("review", {"reviewer": "test_verifier", "decision": verdict,
                          "report_sha256": hashlib.sha256(fe.jcs(verifier_out)).hexdigest(),
                          "passed": res["passed"], "failed": res["failed"], "coverage_bp": cov_bp,
                          "mutation_killed": killed, "mutation_total": total})

    # ---- 4. auditor (fixture output, schema-validated) ---------------------------------
    auditor_out = json.loads((EX / "auditor_findings.json").read_text())
    jsonschema.validate(auditor_out, json.loads((ROOT / "schemas/auditor-findings.schema.json").read_text()))
    gated("compliance_auditor", "finding.file")
    chain.emit("review", {"reviewer": "compliance_auditor", "decision": auditor_out["recommendation"],
                          "findings_sha256": hashlib.sha256(fe.jcs(auditor_out)).hexdigest(),
                          "blockers": sum(f["severity"] == "blocker" for f in auditor_out["findings"])})

    # ---- 5. human approvals with separation of duties (HITL-4.1 / 4.3) ------------------
    approvals = [{"subject": "u-alvarez", "groups": ["grp-ai-policy-owners"]},
                 {"subject": "u-chen", "groups": ["grp-ai-governance-board"]}]
    bad, _ = gt.approval_errors({"requester": "u-alvarez", "signer": "u-okafor", "approvals": approvals}, engine)
    log.append(f"approval check (requester=u-alvarez self-approves) -> errors {sorted(bad)}")
    events.append({"kind": "approval", "scenario": "Requester tries to approve own change", "ok": not bad, "errors": bad})
    good, _ = gt.approval_errors({"requester": "u-patel", "signer": "u-okafor", "approvals": approvals}, engine)
    ok = not good
    log.append(f"approval check (requester=u-patel, approvers alvarez+chen, signer okafor) -> ok={ok}")
    events.append({"kind": "approval", "scenario": "Two authorized approvers, separate signer", "ok": ok, "errors": good})
    assert ok is True
    policy_digest = sha256_file(EX / "policy/ai_code_change.rego")
    chain.emit("policy_approval", {"request_id": REQ, "approvers": [who(a["subject"]) for a in approvals],
                                   "requester": who("u-patel"), "old_policy_sha256": "0" * 64,
                                   "new_policy_sha256": policy_digest, "justification": "new_requirement"})

    # ---- 6. bundle + DSSE --------------------------------------------------------------
    files = {"policy/ai_code_change.rego": EX / "policy/ai_code_change.rego",
             "tests/acceptance_test.rego": EX / "tests/acceptance_test.rego",
             "docs/ai_code_change.md": EX / "docs/ai_code_change.md",
             "reports/verifier.json": None, "reports/auditor.json": None}
    for rel, src in files.items():
        dst = out / "artifacts" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src:
            shutil.copy(src, dst)
    (out / "artifacts/reports/verifier.json").write_text(json.dumps(verifier_out, indent=2))
    (out / "artifacts/reports/auditor.json").write_text(json.dumps(auditor_out, indent=2))
    manifest = {rel: sha256_file(out / "artifacts" / rel) for rel in files}

    statement = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": rel, "digest": {"sha256": d}} for rel, d in manifest.items()],
        "predicateType": "https://aigovops.foundation/foundry/policy-artifact/v0.1",
        "predicate": {
            "request_id": REQ, "policy_id": "acme.ai_code_change", "policy_version": "1.0.0",
            "previous_policy_digest": "none", "requirements": [f"{REQ}.{i}" for i in range(1, 6)],
            "verification": {"verdict": verdict, "coverage_bp": cov_bp, "mutation_bp": mut_bp,
                             "vectors_tree_sha256": vectors_digest},
            "audit": {"recommendation": auditor_out["recommendation"]},
            "approvals": [{"subject_commitment": who(a["subject"]), "role": a["groups"][0],
                           "ts_ns": chain.receipts[-1]["ts_ns"]} for a in approvals],
            "receipt_log": {"merkle_root": "see checkpoint.json", "size": len(chain.receipts)},
            "signing": {"threshold": 2, "algs": ["ed25519"], "prod_algs": ["ed25519", "ml-dsa-65"]},
            "scope_statement": "Signatures prove who signed which bytes and that declared checks ran; "
                               "they do not prove the policy is correct, sufficient, or legally compliant.",
        },
    }
    envelope = fe.dsse_sign(statement, [officer, arbiter])
    (out / "statement.dsse.json").write_text(json.dumps(envelope, indent=2))
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    env_digest = hashlib.sha256(fe.jcs(envelope)).hexdigest()
    chain.emit("bundle_signed", {"request_id": REQ, "envelope_sha256": env_digest,
                                 "signers": [s["keyid"] for s in envelope["signatures"]],
                                 "signing_officer": who("u-okafor")})
    bundle_receipt_index = len(chain.receipts) - 1

    # ---- 7. underwriting evidence packet -----------------------------------------------
    types = [r["type"] for r in chain.receipts]
    gate_decisions = sum(t in ("permit", "denial", "escalation") for t in types)
    packet = {
        "tenant": TENANT, "period": {"start": "2026-07-01", "end": "2026-09-30"},
        "system_inventory": [{"system": "governed-policy-foundry", "agents": 4, "devin_deployment": "customer-dedicated"}],
        "pillars": {"data_privacy": 8000, "security": 8500, "safety": 7000, "reliability": 7500,
                    "accountability": 9000, "society": 5000},
        "metrics": {
            "gate_coverage_bp": 10000,  # of boundary-crossing actions; in-VM actions are NOT covered
            "denial_rate_bp": types.count("denial") * 10000 // gate_decisions,
            "hitl_override_rate_bp": 0, "attestation_gap_count": types.count("attestation_gap"),
            "median_review_latency_s": 0,
        },
        "incidents": [],
        "limitations": [
            "Receipts are operator-signed; no independent notary yet (below OVERT AAL-4).",
            "Commands inside Devin VMs are not intercepted; only actions crossing customer conduits are gated.",
            "Pillar scores are self-assessed control coverage, not an AIUC-1 certification result.",
        ],
        "receipt_log_root": "see checkpoint.json", "risk_tier": "T3",
    }
    jsonschema.validate(packet, json.loads((ROOT / "schemas/underwriting-packet.schema.json").read_text()))
    (out / "underwriting_packet.json").write_text(json.dumps(packet, indent=2))
    chain.emit("underwriting_packet", {"packet_sha256": hashlib.sha256(fe.jcs(packet)).hexdigest(),
                                       "released": False, "release_requires": "risk_officer"})
    chain.emit("session_close", {"request_id": REQ, "disposition": "signed_pending_publish",
                                 "actions": len(chain.receipts) + 1, "open_ref": chain.receipts[0]["counter"]})

    # ---- 8. log, checkpoint, proofs ----------------------------------------------------
    (out / "receipts.ndjson").write_text(chain.ndjson())
    leaves = [fe.jcs(r) for r in chain.receipts]
    root = fe.merkle_root(leaves)
    sth = {"log": "foundry-receipts-acme-mfg", "size": len(leaves), "root": root,
           "ts_ns": chain.receipts[-1]["ts_ns"]}
    checkpoint = dict(sth, witness_keyid=fe.key_id(witness.public_key()), witness_sig=fe.b64(witness.sign(fe.jcs(sth))))
    (out / "checkpoint.json").write_text(json.dumps(checkpoint, indent=2))
    (out / "inclusion_bundle_signed.json").write_text(json.dumps({
        "index": bundle_receipt_index, "size": len(leaves),
        "proof": fe.inclusion_proof(leaves, bundle_receipt_index)}, indent=2))
    for name, k in [("arbiter", arbiter), ("signing_officer", officer), ("witness", witness)]:
        (out / "keys" / f"{name}.ed25519.pub.hex").write_text(pub_raw_hex(k) + "\n")
    shutil.copy(PKG / "evidence.py", out / "foundry_evidence.py")
    shutil.copy(PKG / "verify_bundle.py", out / "verify_bundle.py")
    (out / "devin_payloads.dryrun.json").write_text(json.dumps(
        {k: {kk: vv for kk, vv in v.items() if kk not in ("prompt", "structured_output_schema")} |
            {"prompt_sha256": hashlib.sha256(v["prompt"].encode()).hexdigest()}
         for k, v in {"verifier_phase_A": pa, "writer": pw, "verifier_phase_B": pb}.items()}, indent=2))
    (out / "pipeline_log.txt").write_text("\n".join(log) + "\n")
    return {"request_id": REQ, "receipts": len(chain.receipts), "root": root, "verdict": verdict,
            "coverage_bp": cov_bp, "mutation": f"{killed}/{total}", "tests": res, "log": log, "events": events,
            "gate_engine": "+".join(sorted(engines)), "verifier_engine": verifier_engine}


TEXT_FILES = ["manifest.json", "statement.dsse.json", "receipts.ndjson", "checkpoint.json",
              "inclusion_bundle_signed.json", "underwriting_packet.json", "devin_payloads.dryrun.json"]


def bundle_json(d: pathlib.Path) -> dict:
    """Single-file bundle for browsers and mobile: every file as UTF-8 text, verified client-side."""
    files = {f: (d / f).read_text() for f in TEXT_FILES}
    for p in sorted((d / "artifacts").rglob("*")):
        if p.is_file():
            files["artifacts/" + p.relative_to(d / "artifacts").as_posix()] = p.read_text()
    for p in sorted((d / "keys").glob("*.pub.hex")):
        files["keys/" + p.name] = p.read_text()
    return {"format": "foundry.bundle+json/v0.1", "files": files}


def cli() -> None:
    ap = argparse.ArgumentParser(description="Run the Foundry demo pipeline and write a signed bundle.")
    ap.add_argument("--out", default="out/bundle-REQ-1042")
    ap.add_argument("--engine", default="auto", choices=["auto", "opa", "python"])
    ap.add_argument("--json", action="store_true", help="also write bundle.json next to the bundle")
    a = ap.parse_args()
    r = run(pathlib.Path(a.out), a.engine)
    if a.json:
        pathlib.Path(a.out, "bundle.json").write_text(json.dumps(bundle_json(pathlib.Path(a.out))))
    print("\n".join(r.pop("log")))
    r.pop("events")
    print(json.dumps(r, indent=2))


if __name__ == "__main__":
    cli()
