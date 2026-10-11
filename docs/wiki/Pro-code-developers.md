# Pro-code developers

For developers extending the Python API, TypeScript dashboard, policy gate or deployment code.

> **Start here:** Use Python 3.11 or newer, install the API's dev dependencies, then run its tests.

## Setup

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e "api[dev]"
cd web && npm ci && npm test && npm run build
```

On the macOS blueprint, replace `python3` with
`/opt/homebrew/bin/python3.12`; the image's default `python3` is 3.9.

The policy gate uses OPA 1.21.1 when available; the API also has a parity-tested
Python engine. The dashboard CI uses Node 22. The local setup guide is
[`CONTRIBUTING.md`](../../CONTRIBUTING.md).

## Architecture in ten lines

1. `web/` is a React dashboard with offline demo and live API modes.
2. Hash routing exposes Overview, Gate, Evidence, Verify, Underwriting, Agents, Settings and More.
3. `api/` is a FastAPI service and serves `web/dist` when configured.
4. `role_boundaries.rego` defines the gate policy.
5. Python and TypeScript gate ports are checked against the OPA parity corpus.
6. Human approvals and separation of duties are checked independently from agent actions.
7. The pipeline produces a policy package, reports and evidence.
8. Receipts are signed and hash-chained; a Merkle checkpoint is witness-signed.
9. A DSSE in-toto statement binds the artifact digests and requires two signatures.
10. The browser, API and bundled Python script can verify the bundle.

See [BLUEPRINT.md](../../docs/BLUEPRINT.md) for the full design.

## Repository map

| Area | Purpose |
|---|---|
| `api/app/main.py` | HTTP routes and optional static dashboard |
| `api/foundry/` | Gate, evidence, pipeline, offline verifier |
| `api/foundry/assets/policy/` | Rego source of truth |
| `api/foundry/assets/config/` | Agent roles and capabilities |
| `api/foundry/assets/prompts/` | Agent prompts |
| `api/tests/` | API, evidence, demo and gate parity tests |
| `web/src/` | Dashboard, browser verifier and TypeScript gate |
| `web/public/demo/` | Bundled offline demo evidence |
| `deploy/`, `infra/` | Hosting examples and PrivateLink design |
| `apps/native/` | Tauri desktop and mobile shell |

## API

OpenAPI's interactive UI is `/docs`. If `FOUNDRY_API_TOKEN` is set, `POST /api/runs`
requires a bearer token.

| Method and path | Purpose |
|---|---|
| `GET /healthz`, `GET /api/meta`, `GET /api/agents` | Health, runtime metadata, roles |
| `POST /api/gate/evaluate`, `POST /api/approvals/check` | Evaluate a gate action or approval set |
| `POST /api/runs`, `GET /api/runs`, `GET /api/runs/{id}` | Create or list runs and read one run |
| `GET /api/runs/{id}/bundle.json`, `GET /api/runs/{id}/bundle.zip` | Download a run bundle |
| `POST /api/verify` | Verify a bundle through the API |
| `POST /api/devin/preview` | Build a Devin payload preview; dry-run only |

Environment variables: `FOUNDRY_API_TOKEN`, `FOUNDRY_CORS_ORIGINS`,
`FOUNDRY_GATE_ENGINE`, `FOUNDRY_MAX_RUNS`, `FOUNDRY_WEB_DIST`, `FOUNDRY_PORT`,
`FOUNDRY_TAG`, `VITE_API_BASE` and `FOUNDRY_DEVIN_LIVE`. Never enable
`FOUNDRY_DEVIN_LIVE` on a public deployment.

## Tests and extensions

The reference matrix is 25 OPA policy tests, 1,102 Python tests with OPA and
1,101 plus 1 skipped without OPA, 11 web tests, four Terraform configurations,
and a container smoke test. These counts are the current repo baseline; report
the exact counts from your run.

- For a gate action, follow the [`foundry-gate-change` skill](../../.agents/skills/foundry-gate-change/SKILL.md).
- For an API route, add coverage in `api/tests/test_api.py`; malformed input must
  return a 4xx or a structured failure, never a 500.
- Evidence, receipt, bundle or DSSE predicate changes need an ADR in
  [`docs/decisions/`](../../docs/decisions/).
- See [`docs/HOSTING.md`](../../docs/HOSTING.md) for deploy targets and
  [`apps/native/`](../../apps/native/) for native builds.

[Back to Home](README.md)
