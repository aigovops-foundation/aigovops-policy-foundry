"""
devin_client.py -- Devin v3 API adapter for the Foundry manager (reference).

Endpoints used (Devin v3, service-user auth, keys prefixed cog_):
  POST /v3/organizations/{org_id}/sessions                       UseDevinSessions
  GET  /v3/organizations/{org_id}/sessions/{devin_id}            ViewOrgSessions (or creator)
  GET  /v3/organizations/{org_id}/sessions/{devin_id}/messages   view right on session
  POST /v3/organizations/{org_id}/sessions/{devin_id}/messages   ManageOrgSessions
  POST /v3/organizations/{org_id}/sessions/{devin_id}/archive    ManageOrgSessions
  GET  /v3/enterprise/audit-logs?time_after&time_before          enterprise audit-log permission

DRY RUN by default: nothing is sent unless FOUNDRY_DEVIN_LIVE=1 and DEVIN_API_KEY are set.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import urllib.request

import yaml

ROOT = pathlib.Path(__file__).resolve().parent / "assets"
BASE = os.environ.get("DEVIN_API_BASE", "https://api.devin.ai")

ROLE_SCHEMA = {
    "policy_writer": "schemas/devin-output-policy-writer.schema.json",
    "test_verifier": "schemas/devin-output-test-verifier.schema.json",
}
ROLE_PROMPT = {
    "policy_writer": "prompts/02-policy-writer.md",
    "test_verifier": "prompts/03-test-verifier.md",
}

TERMINAL = {"exit", "error"}
NEEDS_HUMAN = {"waiting_for_approval", "waiting_for_user"}


def load_agents() -> dict:
    return yaml.safe_load((ROOT / "config/agents.yaml").read_text())


def _template(path: str) -> str:
    txt = (ROOT / path).read_text()
    # the template body is the fenced ```text block
    return txt.split("```text", 1)[1].split("```", 1)[0].strip()


def render(path: str, values: dict) -> str:
    out = _template(path)
    if "{{shared_preamble}}" in out:
        out = out.replace("{{shared_preamble}}", _template("prompts/00-shared-preamble.md"))
    for k, v in values.items():
        out = out.replace("{{" + k + "}}", v if isinstance(v, str) else json.dumps(v))
    return out


def build_session_payload(role: str, request_id: str, iteration: int, values: dict,
                          repos_override: list[str] | None = None) -> dict:
    a = load_agents()["agents"][role]
    if repos_override is not None and not set(repos_override) <= set(a["repos"]):
        raise ValueError("repos_override may only narrow the role's repos")
    schema = json.loads((ROOT / ROLE_SCHEMA[role]).read_text())
    prompt = render(ROLE_PROMPT[role], dict(values, request_id=request_id, iteration=str(iteration), role_name=role))
    leftover = sorted(set(re.findall(r"\{\{(\w+)\}\}", prompt)))
    if leftover:
        raise ValueError(f"unfilled prompt placeholders: {leftover}")
    if len(json.dumps(schema)) > 64 * 1024:
        raise ValueError("structured_output_schema exceeds Devin's 64 KB limit")
    return {
        "title": f"[foundry] {request_id} {role} iter{iteration}",
        "prompt": prompt,
        "playbook_id": a["devin_playbook"],
        "security_profile": {"profile_id": a["devin_security_profile"]},
        "repos": repos_override if repos_override is not None else a["repos"],
        "secret_ids": a.get("secret_ids", []),
        "max_acu_limit": a["max_acu_limit"],
        "devin_mode": a.get("devin_mode", "normal"),
        "tags": ["foundry", request_id, f"role:{role}", f"iter:{iteration}"],
        "structured_output_schema": schema,
        "structured_output_required": True,
        "bypass_approval": False,   # keep Devin's own approval prompts on; route them to humans
        "resumable": False,         # disposable VM per agent per iteration
        # create_as_user_id intentionally omitted: no impersonation in the Foundry
    }


def _http(method: str, path: str, body: dict | None = None) -> dict:
    if os.environ.get("FOUNDRY_DEVIN_LIVE") != "1":
        return {"dry_run": True, "method": method, "path": path, "body_keys": sorted((body or {}).keys())}
    key = os.environ["DEVIN_API_KEY"]
    if not key.startswith("cog_"):
        raise ValueError("expected a v3 service-user key (cog_ prefix)")
    req = urllib.request.Request(
        BASE + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:  # egress via allowlisted proxy in prod
        return json.loads(r.read())


def create_session(org_id: str, payload: dict) -> dict:
    return _http("POST", f"/v3/organizations/{org_id}/sessions", payload)


def get_session(org_id: str, devin_id: str) -> dict:
    return _http("GET", f"/v3/organizations/{org_id}/sessions/{devin_id}")


def list_messages(org_id: str, devin_id: str) -> dict:
    return _http("GET", f"/v3/organizations/{org_id}/sessions/{devin_id}/messages")


def archive(org_id: str, devin_id: str) -> dict:
    return _http("POST", f"/v3/organizations/{org_id}/sessions/{devin_id}/archive", {})


def audit_logs(time_after: int, time_before: int) -> dict:
    if time_before - time_after > 100 * 86400:
        raise ValueError("Devin audit-log window must be <= 100 days")
    return _http("GET", f"/v3/enterprise/audit-logs?time_after={time_after}&time_before={time_before}&order=asc")


def classify(session: dict) -> str:
    """Map Devin status/status_detail to a manager state-machine transition."""
    st, det = session.get("status"), session.get("status_detail")
    if st in TERMINAL or det == "finished":
        return "collect"
    if det in NEEDS_HUMAN:
        return "route_to_human"
    if st == "suspended":
        return "escalate"  # usage limits, inactivity, contract etc.
    return "wait"
