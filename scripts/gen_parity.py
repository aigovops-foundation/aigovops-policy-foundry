#!/usr/bin/env python3
"""Generate the gate parity corpus and its OPA-computed golden outputs.

  python3 scripts/gen_parity.py          # rewrite corpus + expected (needs opa)
  python3 scripts/gen_parity.py --check  # CI: recompute with OPA and fail on any drift
"""
import itertools, json, pathlib, subprocess, sys, tempfile, os, shutil
ROOT = pathlib.Path(__file__).resolve().parents[1]
A = ROOT / "api/foundry/assets"
OPA = os.environ.get("OPA_BIN") or shutil.which("opa") or "opa"

agents = ["manager", "policy_writer", "test_verifier", "compliance_auditor", "rogue", "u-chen"]
actions = ["git.push", "git.read", "git.merge", "pr.open", "pr.review.approve", "pr.review.request_changes",
           "opa.test.local", "policy.approve", "artifact.sign", "underwriting.release", "devin.session.create",
           "network.connect", "finding.file", "secret.read", "beacon.receipt.emit"]
targets = [None, "policy-src/main", "policy-src/branches/foundry/REQ-1", "policy-src/branches/foundry/a/b",
           "policy-tests/branches/foundry/REQ-1", "policy-tests/main", "requirements", "policy-src",
           "ot/l2/historian", "ot/", "otx/thing"]
cases = []
for ag, ac, t in itertools.product(agents, actions, targets):
    c = {"agent": ag, "action": ac}
    if t is not None:
        c["target"] = t
    cases.append(c)
W = ["git.read:policy-src", "git.push:policy-src/branches/foundry/*", "pr.open:policy-src", "opa.test.local"]
extra = [
    {"agent": "policy_writer", "on_behalf_of": "compliance_auditor", "action": "git.push", "target": "policy-src/branches/foundry/x"},
    {"agent": "test_verifier", "on_behalf_of": "policy_writer", "action": "git.push", "target": "policy-tests/branches/foundry/x"},
    {"agent": "policy_writer", "on_behalf_of": "nobody", "action": "opa.test.local"},
    {"agent": "policy_writer", "action": "opa.test.local", "depth": 4},
    {"agent": "policy_writer", "action": "opa.test.local", "depth": 3, "identical_call_count": 4},
    {"agent": "manager", "action": "devin.session.create", "delegation": {"to": "policy_writer", "parent_scope": W, "child_scope": W[:2]}},
    {"agent": "manager", "action": "devin.session.create", "delegation": {"to": "policy_writer", "parent_scope": W[:1], "child_scope": W[:2]}},
    {"agent": "manager", "action": "devin.session.create", "delegation": {"to": "test_verifier", "parent_scope": W, "child_scope": W[1:2]}},
    {"agent": "manager", "action": "devin.session.create", "delegation": {"to": "nobody", "parent_scope": W, "child_scope": W[:1]}},
    {"agent": "manager", "action": "devin.session.create", "delegation": {"to": "policy_writer", "child_scope": W[:1]}},
    {"agent": "policy_writer", "action": "devin.session.create", "delegation": {"to": "test_verifier", "parent_scope": W, "child_scope": []}},
    {"agent": "compliance_auditor", "action": "artifact.sign"},
    {"agent": "manager", "action": "devin.session.create", "delegation": {"to": "policy_writer", "parent_scope": [], "child_scope": []}},
    {"agent": "manager", "action": "devin.session.create", "delegation": {"to": "policy_writer", "parent_scope": False, "child_scope": ["opa.test.local"]}},
    {"agent": "manager", "action": "git.merge", "target": "ot/l1/plc"},
]
cases += extra
owner = {"subject": "u-alvarez", "groups": ["grp-ai-policy-owners"]}
board = {"subject": "u-chen", "groups": ["grp-ai-governance-board"]}
rando = {"subject": "u-x", "groups": ["grp-other"]}
agent_ap = {"subject": "compliance_auditor", "groups": ["grp-ai-policy-owners"]}
approvals = []
for req, sig, aps in itertools.product(["u-patel", "u-alvarez"], ["u-okafor", "u-chen"],
                                       [[], [owner], [owner, board], [owner, owner], [owner, rando], [owner, agent_ap], [board, owner, rando]]):
    approvals.append({"requester": req, "signer": sig, "approvals": aps})


def opa_eval(query, data):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump({"parity": data}, f)
    r = subprocess.run([OPA, "eval", "-f", "json", "-d", str(A / "policy/role_boundaries.rego"),
                        "-d", str(A / "config/agents.yaml"), "-d", f.name, query],
                       capture_output=True, text=True, check=True)
    os.unlink(f.name)
    return json.loads(r.stdout)["result"][0]["expressions"][0]["value"]


dec = opa_eval("[d | some c in data.parity.cases; d := data.foundry.gate.decision with input as c]", {"cases": cases})
apr = opa_eval("[x | some c in data.parity.approvals; x := sort([e | some e in data.foundry.gate.approval_errors with input as c])]", {"approvals": approvals})
assert len(dec) == len(cases) and len(apr) == len(approvals)
corpus = {"decisions": cases, "approvals": approvals}
expected = {"decisions": dec, "approvals": apr}
if "--check" in sys.argv:
    old = json.loads((A / "parity/expected.json").read_text())
    oldc = json.loads((A / "parity/corpus.json").read_text())
    if old != expected or oldc != corpus:
        sys.exit("parity golden is stale or Rego changed behaviour: run scripts/gen_parity.py and review the diff")
    print(f"parity golden matches OPA ({len(cases)} decisions, {len(approvals)} approval sets)")
else:
    (A / "parity/corpus.json").write_text(json.dumps(corpus, indent=1) + "\n")
    (A / "parity/expected.json").write_text(json.dumps(expected, indent=1) + "\n")
    from collections import Counter
    print(len(cases), "decision cases", Counter(d["result"] for d in dec), len(approvals), "approval sets")
