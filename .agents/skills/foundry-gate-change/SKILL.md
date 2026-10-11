---
name: foundry-gate-change
description: Safely change the role-boundary gate (Rego) and keep the Python and TypeScript ports in exact parity with OPA.
---
## Change the gate

1. Edit `api/foundry/assets/policy/role_boundaries.rego`. Add tests to `role_boundaries_test.rego`
   first. Missing input fields must fail CLOSED (use `object.get` with a default; never rely on
   `not x in <possibly-undefined ref>`).
2. `opa fmt -w`, `opa check --strict`, `opa test policy/ config/agents.yaml -v`.
3. Add corpus cases for the new behaviour in `scripts/gen_parity.py`, then run it to regenerate
   the golden. Review `git diff api/foundry/assets/parity/expected.json` and explain every changed
   decision in the PR description.
4. Mirror the change in `api/foundry/gate.py` and `web/src/lib/gate.ts`. Both must pass:
   `cd api && pytest -q tests/test_gate_parity.py` and `cd web && npm test`.
5. Regenerate demo data: `python3 scripts/build_demo_data.py`.
6. Never widen an agent's scope without an ADR in `docs/decisions/`.
