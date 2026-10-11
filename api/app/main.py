"""
AiGovOps Policy Foundry API.

FastAPI app named `app` in app/main.py (the layout Devin's Fly.io backend deploy expects).
Serves the gate, approval checks, demo pipeline runs, signed bundles and offline-equivalent
verification. Optionally serves the built web dashboard from FOUNDRY_WEB_DIST.

Environment:
  FOUNDRY_API_TOKEN     if set, POST /api/runs requires `Authorization: Bearer <token>`
  FOUNDRY_CORS_ORIGINS  comma-separated origins (default "*", no credentials)
  FOUNDRY_WEB_DIST      path to web/dist to serve the dashboard from the same origin
  FOUNDRY_MAX_RUNS      runs kept in memory (default 20)
  FOUNDRY_GATE_ENGINE   auto | opa | python (default auto)
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import pathlib
import re
import secrets
import shutil
import tempfile
import time
import uuid
import zipfile
from collections import OrderedDict
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from foundry import devin_client, gate, pipeline
from foundry.verify_bundle import verify as verify_dir

VERSION = "0.1.0"
ENGINE = os.environ.get("FOUNDRY_GATE_ENGINE", "auto")
MAX_RUNS = int(os.environ.get("FOUNDRY_MAX_RUNS", "20"))
WORK = pathlib.Path(tempfile.mkdtemp(prefix="foundry-runs-"))
RUNS: "OrderedDict[str, dict]" = OrderedDict()
RUN_LOCK = asyncio.Semaphore(2)

app = FastAPI(
    title="AiGovOps Policy Foundry API",
    version=VERSION,
    description="Governed multi-agent policy generation: role-boundary gate, approvals, signed bundles, verification.",
)
origins = [o.strip() for o in os.environ.get("FOUNDRY_CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"],
                   allow_headers=["Authorization", "Content-Type"], allow_credentials=False)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    path = request.url.path
    if path.startswith("/api"):
        cache = "no-store"
    elif path.startswith("/assets/"):
        cache = "public, max-age=31536000, immutable"  # content-hashed by Vite
    else:
        cache = "no-cache"  # index.html and demo data: always revalidate after a deploy
    resp.headers.setdefault("Cache-Control", cache)
    return resp


def require_token(authorization: str | None = Header(default=None)) -> None:
    token = os.environ.get("FOUNDRY_API_TOKEN")
    if not token:
        return
    if not authorization or not authorization.startswith("Bearer ") or \
            not secrets.compare_digest(authorization[7:], token):
        raise HTTPException(status_code=401, detail="missing or invalid bearer token")


# ------------------------------------------------------------------ models


class Delegation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    to: str = Field(max_length=64)
    parent_scope: list[str] | None = Field(default=None, max_length=64)
    child_scope: list[str] = Field(default_factory=list, max_length=64)


class GateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent: str = Field(max_length=64)
    action: str = Field(max_length=128)
    target: str | None = Field(default=None, max_length=256)
    on_behalf_of: str | None = Field(default=None, max_length=64)
    delegation: Delegation | None = None
    depth: int = Field(default=0, ge=0, le=100)
    identical_call_count: int = Field(default=0, ge=0, le=1000)


class Approver(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: str = Field(max_length=64)
    groups: list[str] = Field(default_factory=list, max_length=16)


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requester: str = Field(max_length=64)
    signer: str = Field(max_length=64)
    approvals: list[Approver] = Field(max_length=10)


class BundleJSON(BaseModel):
    format: Literal["foundry.bundle+json/v0.1"]
    files: dict[str, str] = Field(max_length=64)


class DevinPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["policy_writer", "test_verifier"]
    request_id: str = Field(default="REQ-1042", pattern=r"^[A-Z]+-[0-9]{1,8}$")
    iteration: int = Field(default=1, ge=1, le=10)


# ------------------------------------------------------------------ routes


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "version": VERSION}


@app.get("/api/meta")
def meta() -> dict:
    return {
        "name": "AiGovOps Policy Foundry",
        "version": VERSION,
        "gate_engine": "opa" if (ENGINE != "python" and gate.opa_bin()) else "python",
        "auth_required_for_runs": bool(os.environ.get("FOUNDRY_API_TOKEN")),
        "devin_mode": "dry-run",
        "assurance": "Operator-signed demo evidence. Not an OVERT conformance claim or certification.",
    }


@app.get("/api/agents")
def agents() -> dict:
    return gate.manifest()


@app.post("/api/gate/evaluate")
def gate_evaluate(req: GateRequest) -> dict:
    inp = req.model_dump(exclude_none=True)
    if inp.get("delegation") is not None and req.delegation and req.delegation.parent_scope is None:
        inp["delegation"].pop("parent_scope", None)
    for k in ("depth", "identical_call_count"):
        if inp.get(k) == 0:
            inp.pop(k)
    decision, used = gate.decide(inp, ENGINE)
    return {"decision": decision, "engine": used, "input": inp}


@app.post("/api/approvals/check")
def approvals_check(req: ApprovalRequest) -> dict:
    errs, used = gate.approval_errors(req.model_dump(), ENGINE)
    return {"ok": not errs, "errors": errs, "engine": used}


def _summary(rid: str, r: dict) -> dict:
    s = r["summary"]
    return {"id": rid, "created": r["created"], "request_id": s["request_id"], "verdict": s["verdict"],
            "receipts": s["receipts"], "root": s["root"], "gate_engine": s["gate_engine"],
            "verifier_engine": s["verifier_engine"]}


def _new_run() -> tuple[str, dict]:
    rid = uuid.uuid4().hex[:12]
    out = WORK / rid
    summary = pipeline.run(out, ENGINE)
    summary.pop("log", None)
    entry = {"dir": out, "created": int(time.time()), "summary": summary}
    RUNS[rid] = entry
    while len(RUNS) > MAX_RUNS:
        _, old = RUNS.popitem(last=False)
        shutil.rmtree(old["dir"], ignore_errors=True)
    return rid, entry


@app.post("/api/runs", dependencies=[Depends(require_token)], status_code=201)
async def create_run() -> dict:
    async with RUN_LOCK:
        rid, _ = await asyncio.to_thread(_new_run)
    return get_run(rid)


@app.get("/api/runs")
def list_runs() -> list[dict]:
    return [_summary(k, v) for k, v in reversed(RUNS.items())]


def _get(rid: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{12}", rid) or rid not in RUNS:
        raise HTTPException(404, "run not found")
    return RUNS[rid]


@app.get("/api/runs/{rid}")
def get_run(rid: str) -> dict:
    r = _get(rid)
    return _summary(rid, r) | {"events": r["summary"]["events"], "tests": r["summary"]["tests"],
                               "coverage_bp": r["summary"]["coverage_bp"], "mutation": r["summary"]["mutation"]}


@app.get("/api/runs/{rid}/bundle.json")
def get_bundle_json(rid: str) -> dict:
    return pipeline.bundle_json(_get(rid)["dir"])


@app.get("/api/runs/{rid}/bundle.zip")
def get_bundle_zip(rid: str) -> Response:
    d = _get(rid)["dir"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(d.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts:
                z.write(p, f"bundle-{rid}/" + p.relative_to(d).as_posix())
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="foundry-bundle-{rid}.zip"'})


SAFE_PATH = re.compile(r"^(?:artifacts/[A-Za-z0-9_./-]+|keys/[A-Za-z0-9_.-]+\.pub\.hex|[A-Za-z0-9_.-]+\.(?:json|ndjson))$")


@app.post("/api/verify")
def verify_bundle(b: BundleJSON) -> dict:
    total = sum(len(v) for v in b.files.values())
    if total > 2_000_000:
        raise HTTPException(413, "bundle too large")
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        for rel, content in b.files.items():
            if not SAFE_PATH.match(rel) or ".." in rel.split("/"):
                raise HTTPException(422, f"unsafe path in bundle: {rel!r}")
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        try:
            return verify_dir(root)
        except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as e:
            return {"ok": False, "checks": [{"name": "structure", "ok": False, "detail": f"{type(e).__name__}: {e}"}]}


@app.post("/api/devin/preview")
def devin_preview(req: DevinPreviewRequest) -> dict:
    """Build (never send) the Devin v3 Create Session payload for a role."""
    values = {"tenant_display_name": "Acme Manufacturing", "risk_tier": "T3", "data_classification": "internal",
              "requirement_text": "(from request record)", "sub_requirements": f"{req.request_id}.1..5",
              "scope_token_id": f"tok-{req.request_id}", "child_scope_list": "[...]",
              "findings_to_address": "[]", "failing_cases": "[]", "phase": "A",
              "writer_branch": "(n/a)", "writer_commit": "(n/a)", "min_coverage_bp": "9000", "min_mutation_bp": "8000"}
    payload = devin_client.build_session_payload(req.role, req.request_id, req.iteration, values)
    return {"endpoint": "POST https://api.devin.ai/v3/organizations/{org_id}/sessions", "dry_run": True,
            "payload": payload}


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception) -> JSONResponse:  # never leak tracebacks
    return JSONResponse({"detail": "internal error", "type": type(exc).__name__}, status_code=500)


# ------------------------------------------------------------------ dashboard (optional)

WEB = os.environ.get("FOUNDRY_WEB_DIST")
if WEB and pathlib.Path(WEB, "index.html").exists():
    app.mount("/assets", StaticFiles(directory=pathlib.Path(WEB, "assets")), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> Any:
        p = (pathlib.Path(WEB) / path).resolve()
        if path and p.is_file() and str(p).startswith(str(pathlib.Path(WEB).resolve())):
            return FileResponse(p)
        return FileResponse(pathlib.Path(WEB, "index.html"))
