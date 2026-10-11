# AGENTS.md

Coding agents (Devin, Claude Code, Codex, Copilot, Cursor and others): read [DEVIN.md](DEVIN.md)
first. It is the build guide for this repository and applies to every agent, not just Devin.

Fast facts:
- Test: `cd api && pytest -q` · `cd web && npm test` · `python3 scripts/gen_parity.py --check`
- Never weaken `api/foundry/assets/policy/role_boundaries.rego` to pass a test.
- Never add certification or conformance claims, secrets, or OT targets.
- Anything public (deploys, releases) needs a human's approval first.
