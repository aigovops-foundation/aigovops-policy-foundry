"""
gate.py -- role-boundary gate.

The Rego policy (assets/policy/role_boundaries.rego) is authoritative. This module evaluates it
with OPA when OPA is installed, and otherwise uses a line-for-line Python port. The port, the
TypeScript port (web/src/lib/gate.ts) and OPA are held together by a shared parity corpus
(assets/parity/): CI fails if any of the three disagree on any case.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

import yaml

ASSETS = Path(__file__).resolve().parent / "assets"
HUMAN_ONLY = {"policy.approve", "artifact.sign", "git.merge", "underwriting.release"}


@lru_cache(maxsize=1)
def manifest() -> dict:
    return yaml.safe_load((ASSETS / "config/agents.yaml").read_text())


def opa_bin() -> str | None:
    p = os.environ.get("OPA_BIN") or shutil.which("opa")
    return p if p and Path(p).exists() else None


# ------------------------------------------------------------------ glob (OPA semantics, "/" delimiter)


@lru_cache(maxsize=512)
def _glob_re(pattern: str) -> re.Pattern:
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$", re.S)


def glob_match(pattern: str, value: str) -> bool:
    return bool(_glob_re(pattern).match(value))


# ------------------------------------------------------------------ python port


def _requested(inp: dict) -> str:
    t = inp.get("target")
    return f"{inp['action']}:{t}" if t else inp["action"]


def _forbidden_hits(agent: dict, inp: dict) -> set[str]:
    req = _requested(inp)
    hits = set()
    for f in agent.get("forbidden", []):
        if ":" not in f and f == inp["action"]:
            hits.add(f)
        elif ":" in f and glob_match(f, req):
            hits.add(f)
    return hits


def _deny_set(inp: dict, data: dict) -> set[str]:
    agents = data["agents"]
    limits = data["runtime_limits"]
    deny: set[str] = set()
    agent = agents.get(inp.get("agent"))
    action = inp["action"]
    req = _requested(inp)

    if agent is None:
        deny.add("unknown-agent")
    else:
        deny |= {f"forbidden:{f}" for f in _forbidden_hits(agent, inp)}
        caps = agent.get("capabilities", [])
        ok = any(c == action or (":" in c and glob_match(c, req)) for c in caps)
        if not ok:
            deny.add("no-matching-capability")

    if action in HUMAN_ONLY:
        deny.add("human-only-action")
    target = inp.get("target", "")
    if isinstance(target, str) and target.startswith("ot/"):
        deny.add("ot-zone-conduit")

    origin = agents.get(inp.get("on_behalf_of")) if inp.get("on_behalf_of") is not None else None
    if origin is not None and _forbidden_hits(origin, inp):
        deny.add("relay-bypass")

    d = inp.get("delegation")
    if d:
        may = (agent or {}).get("may_delegate_to")
        if not (may is not None and d.get("to") in may):
            deny.add("delegation-target-not-allowed")
        if d.get("parent_scope", False) is False:  # Rego `not x`: undefined or false only
            deny.add("delegation-missing-parent-scope")
        parent = d.get("parent_scope") or []
        to_caps = (agents.get(d.get("to")) or {}).get("capabilities") or []
        for c in d.get("child_scope", []) or []:
            if c not in parent:
                deny.add(f"scope-widening:{c}")
            if c not in to_caps:
                deny.add(f"exceeds-role-capability:{c}")

    if inp.get("depth", 0) > limits["max_recursion_depth"]:
        deny.add("recursion-depth-exceeded")
    if inp.get("identical_call_count", 0) > limits["identical_call_repeat_limit"]:
        deny.add("repeat-limit-exceeded")
    return deny


def decide_py(inp: dict, data: dict | None = None) -> dict:
    data = data or manifest()
    deny = _deny_set(inp, data)
    if not deny:
        return {"result": "allow", "reasons": []}
    action = inp["action"]
    benign = {"human-only-action", "no-matching-capability", f"forbidden:{action}"}
    if action in HUMAN_ONLY and deny <= benign:
        return {"result": "escalate", "reasons": sorted(deny)}
    return {"result": "deny", "reasons": sorted(deny)}


def approval_errors_py(inp: dict, data: dict | None = None) -> list[str]:
    data = data or manifest()
    approvals = inp.get("approvals", [])
    subjects = {a["subject"] for a in approvals}
    errs: set[str] = set()
    if len(subjects) < 2:
        errs.add("fewer-than-two-approvers")
    if len({s for s in subjects if s != inp.get("requester")}) < 1:
        errs.add("requester-is-sole-approver")
    if inp.get("requester") in subjects:
        errs.add("requester-counted-as-approver")
    for a in approvals:
        authorized = any(h["idp_group"] in a.get("groups", []) and "policy.approve" in h["may"]
                         for h in data["humans"].values())
        if not authorized:
            errs.add(f"approver-not-authorized:{a['subject']}")
        if a["subject"] in data["agents"]:
            errs.add("agent-cannot-approve")
        if a["subject"] == inp.get("signer"):
            errs.add("signer-also-approver")
    return sorted(errs)


# ------------------------------------------------------------------ OPA


def _opa_eval(query: str, inp: dict) -> object:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(inp, f)
    try:
        out = subprocess.run(
            [opa_bin(), "eval", "-f", "json",
             "-d", str(ASSETS / "policy/role_boundaries.rego"),
             "-d", str(ASSETS / "config/agents.yaml"), "-i", f.name, query],
            capture_output=True, text=True, check=True, timeout=20)
    finally:
        os.unlink(f.name)
    return json.loads(out.stdout)["result"][0]["expressions"][0]["value"]


def decide(inp: dict, engine: str = "auto") -> tuple[dict, str]:
    """Return (decision, engine_used). engine: auto | opa | python."""
    if engine == "opa" or (engine == "auto" and opa_bin()):
        return _opa_eval("data.foundry.gate.decision", inp), "opa"
    return decide_py(inp), "python"


def approval_errors(inp: dict, engine: str = "auto") -> tuple[list[str], str]:
    if engine == "opa" or (engine == "auto" and opa_bin()):
        return sorted(_opa_eval("data.foundry.gate.approval_errors", inp)), "opa"
    return approval_errors_py(inp), "python"
