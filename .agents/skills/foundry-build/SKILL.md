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
