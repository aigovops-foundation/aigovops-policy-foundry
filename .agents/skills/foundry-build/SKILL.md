---
name: foundry-build
description: Build and test every part of the Policy Foundry (policy, API, dashboard, container) and report exact results.
---
## Build and test

1. Read `DEVIN.md` sections "Guardrails" and "Definition of done".
2. Run, in order, and record exact pass/fail counts for each:
   - `cd api/foundry/assets && opa fmt --list --fail policy/ && opa check --strict policy/ && opa test policy/ config/agents.yaml -v`
   - `python3 scripts/gen_parity.py --check`
   - `cd api && pytest -q` and `cd api && OPA_BIN=/nonexistent pytest -q`
   - `cd web && npm test && npm run build`
   - `docker build -t policy-foundry . && docker run -d -p 8000:8000 --name pf policy-foundry`, then
     `curl -fsS localhost:8000/healthz` and `curl -fsS -X POST localhost:8000/api/runs`
3. Open http://localhost:8000 in the browser. Click "Run pipeline", open Evidence, click
   "Tamper with it" on any receipt and confirm the top bar flips to "Not verified", then Restore.
4. Report: every command, its exact counts, and anything you could not run. Never say "all good"
   without numbers.

## Test the dashboard demo

- Before local testing, check the public baseline with `curl -sS -o /dev/null -w '%{http_code}\n' https://aigovops-foundation.github.io/aigovops-policy-foundry/`.
- Build with `cd web && npm ci && npm run build`. Serve `web/dist` as `/aigovops-policy-foundry/` using a plain static server rooted at a parent with an `aigovops-policy-foundry` symlink to `web/dist`; don't use a Vite preview that can proxy API calls.
- The offline demo probes `/api/meta`: 404 on Pages/static hosting is expected; a preview proxy may return 500 without an API. Don't treat that probe alone as a demo failure; check that app assets and bundled demo data load under the subpath.
- Hard-reload hash deep links (for example `/#/policy`) with cache disabled to check subpath routing.
- On phones, Policy and Underwriting are under More. The policy-request issue form may redirect anonymous users to GitHub login; check the destination only and never submit forms or create issues.
