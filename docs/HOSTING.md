# Hosting the Policy Foundry

One container image runs everything: API, dashboard and OPA. Pick a target below.

| Target | Best for | Effort | Default? |
|---|---|---|---|
| [Local container on Mac or Windows](#local-container-mac-windows-linux) | Demos on a laptop, offline | 2 minutes | Demos |
| [Google Cloud Run](#google-cloud-run-default) | Shared demo or pilot | 15 minutes | **Cloud default** |
| [Azure Container Apps](#azure-container-apps) | Microsoft shops | 15 minutes | |
| [AWS ECS Fargate](#aws-ecs-fargate) | AWS shops; pairs with the PrivateLink design | 30 minutes | |
| [Any Kubernetes](#any-kubernetes) | Existing clusters (EKS, GKE, AKS, OpenShift, k3s) | 10 minutes | |
| [Fly.io / any container host](#flyio-or-any-container-host) | Render, Railway, Koyeb, DigitalOcean, Fly | 10 minutes | |
| [Hosted by Devin](#hosted-by-devin) | Fastest public preview from a Devin session | 5 minutes | |
| [Static dashboard only](#static-dashboard-only) | GitHub Pages, Netlify, Vercel, S3, any CDN | 5 minutes | |
| [GitHub Pages (static demo)](#github-pages-static-demo) | Public offline exploration of bundled demo evidence | No install | Public demo |

Security defaults for every non-local target: set `FOUNDRY_API_TOKEN` from a secret store, keep the
service private unless it is an intentional public demo, and never set `FOUNDRY_DEVIN_LIVE=1`.

---

## Local container (Mac, Windows, Linux)

Needs one of: Docker Desktop, Podman Desktop, OrbStack, Colima or Rancher Desktop. Apple Silicon
and Intel both work (the image is multi-arch).

**macOS / Linux**
```sh
git clone https://github.com/aigovops-foundation/aigovops-policy-foundry
cd aigovops-policy-foundry
./scripts/demo.sh            # builds, starts, waits for health, opens http://localhost:8000
```

**Windows 10/11** (Docker Desktop with WSL 2, or Podman Desktop), in PowerShell:
```powershell
git clone https://github.com/aigovops-foundation/aigovops-policy-foundry
cd aigovops-policy-foundry
powershell -ExecutionPolicy Bypass -File scripts\demo.ps1
```

Or directly: `docker compose up --build`. Stop with `docker compose down`.
The port binds to `127.0.0.1` only; change `FOUNDRY_PORT` to use another port.

No container engine? Run the two processes natively:
```sh
pip install -e "api[dev]"; (cd web && npm ci && npm run build)
cd api && FOUNDRY_WEB_DIST=../web/dist uvicorn app.main:app --port 8000
```
Without OPA installed the API uses the parity-tested Python gate and a recorded verifier result;
the dashboard labels both.

## Google Cloud Run (default)

```sh
cd deploy/gcp
terraform init
# 1) create the registry first
terraform apply -target=google_artifact_registry_repository.foundry -var project_id=$PROJECT -var image=placeholder
# 2) build and push
REG=$(terraform output -raw registry)
gcloud auth configure-docker ${REG%%/*}
docker buildx build --platform linux/amd64 -t $REG/aigovops-policy-foundry:0.1.0 --push ../..
# 3) deploy (private by default; add -var public=true only for an intentional public demo)
terraform apply -var project_id=$PROJECT -var image=$REG/aigovops-policy-foundry:0.1.0
```
The API token lives in Secret Manager (`terraform output api_token_secret`). The runtime service
account has no project roles beyond reading that secret.

## Azure Container Apps

```sh
cd deploy/azure && terraform init
az acr create -g rg-policy-foundry -n <acrname> --sku Basic   # or use GHCR
docker buildx build --platform linux/amd64 -t <acrname>.azurecr.io/aigovops-policy-foundry:0.1.0 --push ../..
terraform apply -var subscription_id=$SUB -var image=<acrname>.azurecr.io/aigovops-policy-foundry:0.1.0
terraform output -raw api_token
```
Ingress is internal unless `-var public=true`.

## AWS ECS Fargate

```sh
cd deploy/aws && terraform init
terraform apply -target=aws_ecr_repository.foundry -var vpc_id=... -var 'public_subnet_ids=[...]' -var 'private_subnet_ids=[...]' -var image=placeholder
REPO=$(terraform output -raw ecr_repository)
aws ecr get-login-password | docker login --username AWS --password-stdin ${REPO%%/*}
docker buildx build --platform linux/arm64 -t $REPO:0.1.0 --push ../..
terraform apply -var vpc_id=... -var 'public_subnet_ids=[...]' -var 'private_subnet_ids=[...]' -var image=$REPO:0.1.0 -var certificate_arn=<acm-arn>
```
Tasks run on Graviton (ARM64) in private subnets with a read-only root filesystem. Narrow
`allowed_cidrs` for non-public demos. For the governed enterprise design with Devin over
PrivateLink, see `infra/privatelink/` and `docs/BLUEPRINT.md` §12.

## Any Kubernetes

```sh
kubectl apply -f deploy/kubernetes/foundry.yaml
kubectl -n policy-foundry create secret generic foundry-api --from-literal=token=$(openssl rand -hex 20)
kubectl -n policy-foundry port-forward svc/policy-foundry 8000:80
```
The namespace enforces the `restricted` Pod Security Standard. Add your own Ingress.

## Fly.io or any container host

Fly: `fly launch --no-deploy --copy-config --config deploy/fly/fly.toml`, then
`fly secrets set FOUNDRY_API_TOKEN=...` and `fly deploy --config deploy/fly/fly.toml`.

Render, Railway, Koyeb, DigitalOcean App Platform and similar: point them at the repo's
`Dockerfile`, expose port 8000, health check `/healthz`, set `FOUNDRY_API_TOKEN`.

## Hosted by Devin

Devin can publish what it builds: static frontends on `devinapps.com` and FastAPI backends on
Fly.io. Every deploy needs your approval in the session. See `deploy/devin/README.md` for the exact
prompt. The repo already fits Devin's backend rules (`api/pyproject.toml` with a project name, and a
FastAPI app named `app` in `api/app/main.py`).

Note: Devin generates its own Dockerfile for the backend, which won't include OPA. The API then
uses the parity-tested Python gate and a recorded verifier result, and says so in `/api/meta` and
on the dashboard. For OPA in production, use one of the container targets above.

## Static dashboard only

The dashboard is fully usable offline with bundled demo evidence, including on-device verification.
```sh
cd web && npm ci && npm run build      # upload web/dist to any static host
# to point it at an API at build time:
VITE_API_BASE=https://foundry.example.com npm run build
```
Users can also connect an API at runtime from Settings.

## GitHub Pages (static demo)

Open the [public browser demo](https://aigovops-foundation.github.io/aigovops-policy-foundry/).
This public demo was approved by the maintainer and contains bundled demo data only.
It is a static dashboard with on-device verification; no data leaves your device.

The `pages.yml` workflow builds and publishes `web/dist` to GitHub Pages when changes
to `web/` merge to `main`. A maintainer must set **Settings → Pages → Source** to
**GitHub Actions** once.

## Desktop and mobile apps

See `apps/native` and the `foundry-native-app` skill. Builds for Windows, macOS, Linux, Android
and iOS come from `.github/workflows/native.yml` as unsigned artifacts. Store distribution needs
Foundation-owned signing credentials and Review Circle sign-off.
