---
name: foundry-deploy
description: Deploy the Policy Foundry to local Docker, Google Cloud (default), Azure, AWS, Kubernetes, Fly.io, or Devin-hosted apps.
argument-hint: <local|gcp|azure|aws|kubernetes|fly|devin>
triggers: ["user"]
---
## Deploy to $1

Follow `docs/HOSTING.md` for target `$1`. Rules:

1. Every public deployment needs explicit human approval. Stop and ask before any command that
   makes something reachable from the internet (`terraform apply`, `fly deploy`, Devin deploy).
2. Never set `FOUNDRY_DEVIN_LIVE=1` on a deployed instance. Set `FOUNDRY_API_TOKEN` from a secret store.
3. Run `terraform validate` and show `terraform plan` output to the human before `apply`.
4. After deploy, verify: `GET /healthz` is 200, `GET /api/meta` shows the expected gate engine,
   `POST /api/runs` (with the token) returns verdict `pass`, and the dashboard loads.
5. Report the URL, the image tag or digest deployed, and how to tear it down.
