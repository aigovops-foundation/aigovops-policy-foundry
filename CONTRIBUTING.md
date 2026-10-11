# Contributing to the AiGovOps Policy Foundry

Thanks for being here. This project is built by people who care about shipping AI safely, and we'd
love to build it with you.

## The shortest version

- Use it. Break it. Tell us what you found.
- Open an issue first if you're not sure.
- Send a small PR. Small PRs get merged.
- Be kind. See [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## How changes land

- **`main` is protected.** Every change goes through a pull request that needs one approving review
  from a maintainer, a green CI run, and signed commits where possible.
- Force-pushes and branch deletions are blocked on `main`.
- Every GitHub Action is pinned to a full commit SHA with the version in a comment. Dependabot
  proposes bumps; a maintainer reviews them.
- Bigger things (a new agent role, a receipt schema change, a change to a governance doc) start
  with an ADR in [`docs/decisions/`](docs/decisions/).

## Run everything locally

```sh
# API + evidence + gate parity (Python 3.11+, OPA optional but recommended)
pip install -e "api[dev]" && (cd api && pytest -q)
# Policy tests and parity golden (needs OPA 1.x)
(cd api/foundry/assets && opa test policy/ config/agents.yaml && opa test examples/req-1042/)
python3 scripts/gen_parity.py --check
# Dashboard
(cd web && npm ci && npm test && npm run build)
# Whole stack in a container
docker compose up --build
```

## Testing expectations

| Layer | Add a test when you... | Where |
|---|---|---|
| Policy | change `role_boundaries.rego` | `role_boundaries_test.rego`, then `scripts/gen_parity.py` and review the golden diff |
| Parity | change the gate in any language | the corpus in `scripts/gen_parity.py`; Python and TypeScript must match OPA exactly |
| Evidence | touch canonicalization, signing, Merkle, DSSE | `api/tests/test_evidence.py` and `web/tests/evidence.test.ts` |
| API | add or change a route | `api/tests/test_api.py` (malformed input must get a 4xx or a structured failure, never a 500) |
| UI | change a user-facing flow | `web/tests/`, plus screenshots in the PR at desktop and phone widths |

Tests must be deterministic. If you change the gate, regenerate the golden with OPA and explain
every changed decision in the PR.

## What's likely to get a "let's talk first"

- Anything that changes the receipt schema, the bundle format or the DSSE predicate.
- Anything that gives an agent a new capability, or weakens a forbidden rule.
- Anything that claims conformance or certification. We say "OVERT-aligned", never "certified".
- Live calls to Devin or any external service from the public API.

## Style

- Code: match the file you're in.
- Docs: plain language, short sentences, kindness. If a sentence would survive in a contract,
  rewrite it.
- Commits: imperative mood ("Add", "Fix"). One-line summary, blank line, paragraph if needed.

## Becoming a maintainer

You don't apply. You earn it: send PRs, review other people's PRs, answer issues. A maintainer
nominates you and the others agree. See [`MAINTAINERS.md`](MAINTAINERS.md).

## Questions

- Issues: https://github.com/aigovops-foundation/aigovops-policy-foundry/issues
- Community: https://www.aigovops-foundation.com/
- Email: bob.rapp@aigovops.community, ken.johnston@aigovops.community
