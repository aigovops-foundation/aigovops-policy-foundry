# AGENTS.md

Coding agents (Devin, Claude Code, Codex, Copilot, Cursor and others): read [DEVIN.md](DEVIN.md)
first. It is the build guide for this repository and applies to every agent, not just Devin.

Setup:
- Python 3.11+: `python3 -m venv .venv && . .venv/bin/activate && pip install -e "api[dev]"`
  (macOS blueprint: use `/opt/homebrew/bin/python3.12`; its `python3` is 3.9)
- Dashboard: `cd web && npm ci`

Fast facts:
- Test: `cd api && pytest -q` · `cd web && npm test` · `python3 scripts/gen_parity.py --check`
- Never weaken `api/foundry/assets/policy/role_boundaries.rego` to pass a test.
- Never add certification or conformance claims, secrets, or OT targets.
- Anything public (deploys, releases) needs a human's approval first.
- Persona docs: `docs/wiki/` is the human-written source; update it when behavior changes.
- Devin skills: `foundry-build`, `foundry-deploy`, `foundry-gate-change`,
  `foundry-verify-evidence`, `foundry-explain`, `foundry-wiki-update`.
- Review guidance: see [REVIEW.md](REVIEW.md).
