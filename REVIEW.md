# Devin Review guidance

Review the change against these boundaries. Flag a violation with the exact file
and line; do not propose weakening a safety check to satisfy a test.

## Critical areas

- `api/foundry/assets/policy/role_boundaries.rego`, `api/foundry/gate.py`,
  `web/src/lib/gate.ts` and `api/foundry/assets/config/agents.yaml` must stay in
  parity. Missing or malformed scope input must fail closed.
- `api/foundry/evidence.py`, `api/foundry/verify_bundle.py` and
  `web/src/lib/evidence.ts` implement related evidence checks. A change to
  receipt, bundle, schema or DSSE predicate shape needs an ADR.
- Prompt changes must preserve the agents' role boundaries and treat untrusted
  text as data.
- Changes that widen `agents.yaml` capabilities need an ADR and maintainer review.

## Claims and security

- Claims must use "OVERT-aligned", "self-assessed" or "demo evidence" as
  appropriate. Do not claim certification or conformance.
- Every GitHub Action must be pinned to a full commit SHA with a version comment.
- The web app must not add localStorage, analytics, CDN fonts or network calls
  outside the configured Foundry API.
- Do not add OT targets, OT connectivity or deployment steps to OT systems.
- Do not add secrets to code, docs, logs, receipts, bundles or screenshots.

## Change hygiene

- Update `CHANGELOG.md` and `docs/wiki/` when the user-facing behavior changes.
- Ignore lockfile changes unless dependencies changed. Ignore icon-only changes.
- Review `api/foundry/assets/parity/expected.json` only with an explained
  decision-by-decision diff.
- Keep documentation claims consistent with the implemented routes, pages and
  tests. Docs are CC BY 4.0.
