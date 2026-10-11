# Host the Policy Foundry with Devin

Devin can publish two things to Cognition-hosted infrastructure, and each deploy waits for your
approval in the session:

- the **dashboard** (`web/dist`) as a static site at `https://<name>.devinapps.com`
- the **API** (`api/`) as a FastAPI backend on Fly.io

The repo already meets Devin's backend requirements: `api/pyproject.toml` has a project name, and
`api/app/main.py` exposes a FastAPI app named `app`.

## Prompt to paste into a Devin session

```text
Read DEVIN.md, then deploy the AiGovOps Policy Foundry using Devin app deployments:

1. Deploy the backend in api/ to Fly.io. Set the secret FOUNDRY_API_TOKEN to a new random value
   and FOUNDRY_CORS_ORIGINS to the devinapps.com URL you will create in step 2. Never set
   FOUNDRY_DEVIN_LIVE.
2. Build the dashboard with VITE_API_BASE set to the backend URL from step 1:
   cd web && npm ci && VITE_API_BASE=<backend-url> npm run build
   Deploy web/dist as a static frontend.
3. Verify: GET <backend>/healthz is 200; GET <backend>/api/meta works; the dashboard loads and shows
   "Live API"; Overview > Run pipeline completes with 20/20 receipts verified.
4. Report both URLs, the token location, and how to delete both deployments.
Ask me before each deploy.
```

## What to expect

- Devin generates its own Dockerfile and `fly.toml` for the backend. That image will not contain
  OPA, so the API runs the parity-tested Python gate and replays the recorded verifier result. The
  dashboard and `/api/meta` label this. For OPA, deploy the repo `Dockerfile` instead (any target in
  `docs/HOSTING.md`, including `deploy/fly/fly.toml`).
- `POST /api/runs` needs the bearer token when `FOUNDRY_API_TOKEN` is set. The dashboard's
  "Run pipeline" button is for token-less demo deployments; for a protected deployment, call the
  API with the token or keep the dashboard in offline demo mode.
- Devin app deployments are for previews. For a pilot inside a manufacturer, use Google Cloud Run,
  Azure or AWS with SSO in front.
