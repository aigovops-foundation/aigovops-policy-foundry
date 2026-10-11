# AiGovOps Policy Foundry

**Governed AI agents that write, test, audit and sign governance policy, with evidence anyone can verify.**

An AiGovOps Foundation incubation project. Apache-2.0 code, CC BY 4.0 docs. Status: **incubating, v0.1.0, pre-release review pending.**

![Policy Foundry dashboard](docs/images/overview-desktop.png)

## What it does

A manufacturer submits a requirement, for example "AI-assisted changes to plant software must be human-reviewed and never go straight into an OT zone." Four agents turn it into a signed policy package:

| Agent | Does | Can never |
|---|---|---|
| Manager | Plans, delegates narrowed scopes, runs the loop | Write code, approve, sign |
| Policy Writer (Devin session) | Drafts executable Rego and a plain-language policy | Edit tests, merge, reach OT |
| Test Verifier (Devin session) | Writes tests **before** seeing the draft, then runs tests and mutation checks | Edit the policy |
| Compliance Auditor (separate model) | Maps controls, finds conflicts, can block | Approve |

A **gate** checks every action that crosses a system boundary and writes a signed receipt. Two people approve (never the requester), a third person signs, and the result is a **bundle**: policy, tests, reports, a dual-signed DSSE statement, a hash-chained receipt log, a witnessed Merkle checkpoint, and an offline verifier. An **underwriting packet** summarizes the evidence for insurers, with its limitations listed first.

## Try it

| You want to... | Do this |
|---|---|
| Find the path for your role | Start at [docs/wiki](docs/wiki/README.md) |
| See it on your laptop (Mac, Windows, Linux) | `./scripts/demo.sh` or `scripts\demo.ps1` (Docker Desktop or Podman), then open http://localhost:8000 |
| Deploy to the cloud | Google Cloud Run (default), Azure Container Apps or AWS ECS Fargate: see [docs/HOSTING.md](docs/HOSTING.md) |
| Have Devin host it | Dashboard on devinapps.com, API on Fly.io: see [deploy/devin](deploy/devin/README.md) |
| Run any other way | Kubernetes, Fly.io, Render, any container host, or the static dashboard alone |
| Build it with Devin | Point Devin at [DEVIN.md](DEVIN.md) |
| Desktop or mobile app | Tauri 2 builds for Windows, macOS, Linux, Android and iOS: [apps/native](apps/native) |

Persona pages: [policy and governance](docs/wiki/Policy-and-governance.md) ·
[low-code builders](docs/wiki/Low-code-builders.md) ·
[pro-code developers](docs/wiki/Pro-code-developers.md) ·
[regulators, auditors and insurers](docs/wiki/Regulators-auditors-and-insurers.md) ·
[end users](docs/wiki/End-users.md).

The dashboard works fully offline with bundled demo evidence. Open **Evidence**, click **Tamper with it** on any receipt, and watch verification fail on your own device.

## What's in the box

- **Dashboard** (`web/`): React app with on-device verification. Same code runs in browsers and the native apps.
- **API** (`api/`): FastAPI. Gate, approvals, demo pipeline runs, bundles (JSON and zip), server-side verification, dry-run Devin payloads. OpenAPI docs at `/docs`.
- **Gate** (`api/foundry/assets/policy/`): Rego is authoritative. Python and TypeScript ports are held to OPA's answers by a 1,033-case parity corpus in CI.
- **Evidence core**: RFC 8785 canonical JSON, Ed25519, keyed commitments, hash-chained receipts, RFC 6962 Merkle proofs, DSSE with two signatures.
- **Native apps** (`apps/native/`): Tauri 2 shell for desktop and mobile.
- **Deploy** (`deploy/`, `infra/`): container, Terraform for GCP, Azure and AWS, Kubernetes, Fly.io, and the PrivateLink design for Devin's Customer Dedicated Deployment.
- **Architecture**: [docs/BLUEPRINT.md](docs/BLUEPRINT.md) covers agent roles, system prompts, the Devin v3 API integration, the Beacon runtime gate, OVERT-aligned receipts, signing, PrivateLink and the underwriting pipeline.

## Tests

| Suite | Count |
|---|---|
| OPA policy tests | 25 |
| Python (evidence, gate parity, API end to end, demo bundle) | 1,102 |
| TypeScript (verifier on the Python-built bundle, gate parity) | 11 |
| Terraform validate | 4 configurations |
| Container smoke test (build, run, pipeline, verify, offline verifier from zip) | CI |

The parity corpus found a fail-open bug in the gate before release: a delegation without `parent_scope` was allowed. Fixed, with regression tests. See [CHANGELOG.md](CHANGELOG.md).

## What this is not

- Not a certification, an OVERT conformance claim, or an AIUC-1 result. Receipts are operator-signed demo evidence, below OVERT AAL-4.
- Not legal advice. Signatures prove who signed which bytes and that the log was not edited; they do not prove a policy is correct or compliant.
- Not affiliated with or endorsed by Cognition (Devin), Glacis (OVERT) or any cloud provider. See [NOTICE](NOTICE).

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md), [GOVERNANCE.md](GOVERNANCE.md) and the [Code of Conduct](CODE_OF_CONDUCT.md). Report security issues privately per [SECURITY.md](SECURITY.md).
