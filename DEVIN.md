# DEVIN.md — Build guide for Devin (and any coding agent)

You are working in **AiGovOps Policy Foundry**, an AiGovOps Foundation incubation project
(Apache-2.0 code, CC BY 4.0 docs). Read this file fully before you change anything. It tells you
what exists, what to build, the rules you must not break, and how to prove you're done.

Companion files:
- `docs/BLUEPRINT.md` — the full architecture (agent roles, Devin API integration, Beacon gate,
  OVERT receipts, PrivateLink, signing, underwriting).
- `docs/HOSTING.md` — every hosting option, step by step.
- `.devin/blueprint.yaml` — your environment (OPA, Terraform, Rust, Node, Python).
- `.agents/skills/` — `foundry-build`, `foundry-deploy`, `foundry-gate-change`, `foundry-native-app`.

---

## 1. What this product is (one paragraph)

A manufacturer wants AI governance policies written, tested, audited, approved and signed quickly,
with evidence an auditor or insurer can check without trusting anyone. Four agents do the work
(Manager, Policy Writer, Test Verifier, Compliance Auditor). A role-boundary **gate** checks every
action that crosses a system boundary and writes a **signed receipt**. Only humans approve, merge
and sign. The output is a **bundle**: the policy, its tests, reports, a dual-signed DSSE statement,
the receipt log, a witnessed Merkle checkpoint and an offline verifier. The same evidence feeds an
**underwriting packet** with its limitations stated up front.

## 2. Two different uses of Devin — don't mix them up

| | What | Where it lives |
|---|---|---|
| **A. Devin builds this repo** | You, following this file, build, test, package and host the app. | This file, `.devin/`, `.agents/skills/` |
| **B. The product uses Devin** | In a live enterprise deployment, the Manager creates Devin sessions (via the Devin v3 API) for the Policy Writer and Test Verifier, inside strict scopes. | `api/foundry/devin_client.py`, `api/foundry/assets/prompts/`, `docs/BLUEPRINT.md` §7 |

The public API only builds **dry-run** Devin payloads (`POST /api/devin/preview`). Live session
creation exists in `devin_client.py` behind `FOUNDRY_DEVIN_LIVE=1` and a `cog_` service-user key, and
must never be enabled on a public deployment.

## 3. Repository map

```
api/                      Python 3.11+ (FastAPI). Devin-deployable: app named `app` in app/main.py
  app/main.py             HTTP API (+ serves web/dist when FOUNDRY_WEB_DIST is set)
  foundry/evidence.py     RFC 8785 JCS, keyed commitments, signed hash-chained receipts, RFC 6962 Merkle, DSSE
  foundry/gate.py         Gate: OPA if installed, else a parity-tested Python port
  foundry/pipeline.py     End-to-end demo pipeline -> signed bundle (+ bundle.json for browsers)
  foundry/verify_bundle.py Offline verifier (also copied into every bundle)
  foundry/devin_client.py Devin v3 adapter (dry-run by default)
  foundry/assets/         config/agents.yaml, policy/*.rego, prompts/, schemas/, examples/, parity/
  tests/                  pytest: evidence, gate parity (1,033 cases), API e2e, demo bundle
web/                      React 19 + Vite dashboard. Offline demo + live API mode. Hash routing.
  src/lib/evidence.ts     Same verifier in TypeScript (on-device verification)
  src/lib/gate.ts         Same gate in TypeScript (parity-tested against OPA)
  public/demo/            Bundled demo evidence (regenerate: scripts/build_demo_data.py)
apps/native/              Tauri 2 shell -> Windows, macOS, Linux, Android, iOS apps from web/dist
deploy/                   gcp (default), azure, aws, kubernetes, fly, devin
infra/privatelink/        Governed production network: Devin dedicated tenant -> PrivateLink -> gate
scripts/                  demo.sh / demo.ps1 (local container), gen_parity.py, build_demo_data.py
docs/                     BLUEPRINT.md, HOSTING.md, decisions/ (ADRs)
```

## 4. Guardrails (non-negotiable)

1. **Never weaken the gate to pass a test.** Change `role_boundaries.rego` only with the
   `foundry-gate-change` skill. Missing input must fail closed. Python and TypeScript ports must
   match OPA on every parity case.
2. **No agent approves, merges, signs or releases.** Don't add code paths that let one.
3. **No OT reachability.** Nothing in this repo may connect to or generate deployment steps for
   plant-floor (OT) systems.
4. **No claims of certification or conformance.** Say "OVERT-aligned", "self-assessed", "demo
   evidence". Never "certified", "compliant" or "AAL-4".
5. **No secrets in the repo, logs, receipts or the dashboard.** Use your secrets manager and env vars.
6. **Pin every GitHub Action to a full commit SHA** with the version in a trailing comment.
7. **Anything public needs a human's approval first**: deploys, releases, store submissions,
   making URLs public. Prepare everything, then stop and ask.
8. **Foundation process:** bigger changes need an ADR in `docs/decisions/`; releases need
   Review Circle sign-off (`RELEASING.md`). Keep `main` green.
9. **Report exact numbers.** "Passed 1,102 of 1,102", not "tests pass". Say what you could not run.

## 5. Current state (v0.1.0)

Done and tested in CI:
- Gate (Rego + Python + TypeScript) with a 1,005-decision / 28-approval parity corpus.
- Evidence core, pipeline, offline verifier; tamper detection tests in Python and TypeScript.
- FastAPI service with input validation, optional bearer token, path-traversal protection.
- Dashboard: Overview, Gate playground, Evidence (with tamper demo), Verify, Underwriting, Agents,
  Settings. Responsive (sidebar on desktop, bottom tabs on phones), light/dark, offline demo mode.
- Container (multi-arch, non-root, read-only rootfs, checksum-verified OPA) and local scripts.
- Terraform for Cloud Run, Azure Container Apps, ECS Fargate, and the PrivateLink design.
- Tauri 2 config, icons for every platform, and a native build workflow.

Not done yet (your backlog, in order — see §6):
- First green run of the native workflow on all five platforms (desktop matrix, Android, iOS).
- Accessibility pass with a real screen reader (VoiceOver, NVDA, TalkBack).
- Persisting API URL/theme in the native apps (Tauri store plugin); the web build stays stateless.
- A live, authenticated deployment on Google Cloud Run (default) after human approval.
- Live Devin integration in a sandbox org (feature-flagged, never on public deployments).
- Store-ready signing for macOS/iOS/Windows/Android (human-owned credentials).

## 6. Work plan for Devin

Do the phases in order. Each ends with a PR, green CI, and a short report with exact numbers.

### Phase 0 — Environment (one time)
Sync `.devin/blueprint.yaml` (Settings > Environment > Blueprints > Sync). Start a session and run
the `foundry-build` skill. Expect: 25/25 OPA tests, parity golden current, 1,102 pytest (OPA) and
1,101 + 1 skipped (no OPA), 11 vitest, web build OK, container smoke test OK.

### Phase 1 — Dashboard and API polish (web + api)
Goal: simple and compelling UX on every screen size.
- Keep the information architecture: Overview → Gate → Evidence → Verify → (Underwriting, Agents, Settings).
- Every screen must answer one question in under five seconds:
  Overview "Is this policy trustworthy?", Gate "What can each agent do?", Evidence "Has anything
  been changed?", Verify "Does this file check out?", Underwriting "What would an insurer see?".
- Add: keyboard shortcuts on desktop (g o, g g, g e, g v), empty and error states for a
  disconnected API, a "Copy as JSON" button on receipts, and screen-reader labels on every icon.
- Write a Playwright smoke test (`web/tests/e2e`) covering: run pipeline (live), tamper + restore,
  verify uploaded file, gate preset decisions, approval check. Run at 1440×900 and 390×844.
- Do not add analytics, trackers, third-party fonts from CDNs, or localStorage in the web build.

### Phase 2 — Native apps (apps/native)
Use the `foundry-native-app` skill.
- Get `native.yml` green on ubuntu-22.04, windows-latest, macos-latest (universal), Android
  debug APK and iOS simulator build. Fix config, not the dashboard, unless a webview bug forces it.
- Add `tauri-plugin-store` to persist API URL and theme in native builds only (feature-detect
  `window.__TAURI__`). Keep the web build stateless.
- Mobile: respect safe areas (already in CSS), test the bottom tab bar on a 6.1" iPhone simulator
  and a Pixel emulator, and verify the file picker on Verify works on both.

### Phase 3 — Hosting (deploy/)
Use the `foundry-deploy` skill. Prepare every target; deploy only what a human approves.
- Local: `scripts/demo.sh` (macOS/Linux) and `scripts/demo.ps1` (Windows) must work with Docker
  Desktop and Podman.
- Google Cloud Run is the default cloud. Then Azure Container Apps and AWS ECS Fargate.
- Devin-hosted option: dashboard on `devinapps.com`, API on Fly.io (see `deploy/devin/README.md`).

### Phase 4 — Live Devin integration (sandbox only)
- In a sandbox Devin org with a dedicated service user (`UseDevinSessions`, `ViewOrgSessions`,
  `ManageOrgSessions` only), wire `devin_client.create_session` into the pipeline behind
  `FOUNDRY_DEVIN_LIVE=1`. Validate every structured output against the schemas in
  `api/foundry/assets/schemas/`. Keep `bypass_approval=false`, `resumable=false`, no
  `create_as_user_id`. Route `waiting_for_approval` to a human.
- Add a reconciliation job that compares Devin audit logs with receipts (BLUEPRINT §7.4).

### Phase 5 — Release candidate
Follow `RELEASING.md`. Prepare the release PR and stop for Review Circle sign-off.

## 7. Definition of done (every PR)

- [ ] CI green: policy, api (both engines), web, terraform (4 dirs), container smoke test.
- [ ] If the gate changed: parity golden regenerated, every changed decision explained.
- [ ] If the UI changed: screenshots at 1440×900 and 390×844, light and dark, attached to the PR.
- [ ] No new network calls from the dashboard except to the configured Foundry API.
- [ ] No secrets, no certification language, no OT targets.
- [ ] `CHANGELOG.md` updated.

## 8. UX principles (keep it simple and compelling)

- One primary action per screen. Plain words: "Allow", "Deny", "Escalate to a human", "Verified".
- Show proof, not adjectives: counts (20/20 receipts, 10/10 tests, 7/7 mutants, 2/2 signatures).
- Make trust tangible: the tamper button is the product demo. Keep it one click from Evidence.
- Offline first: the app must be fully explorable with no network, including verification.
- Same UI everywhere: browser, desktop and mobile use one codebase (`web/`). Native shells add
  only OS integration (window, file access, links, store).
- Accessibility: WCAG 2.2 AA contrast, 44px touch targets on phones, visible focus, reduced motion.

## 9. Useful commands

```sh
python3 scripts/build_demo_data.py         # regenerate dashboard demo bundle (after pipeline changes)
python3 scripts/gen_parity.py              # regenerate gate golden (after Rego changes; needs OPA)
cd api && foundry-demo --out /tmp/b --json && foundry-verify /tmp/b
cd api && uvicorn app.main:app --reload    # http://localhost:8000/docs
cd web && npm run dev                      # http://localhost:5173
docker compose up --build                  # http://localhost:8000
```
