# Low-code builders

For people who edit YAML or JSON and use forms and buttons, rather than writing Python.

> **Start here:** Open the [browser demo](https://aigovops-foundation.github.io/aigovops-policy-foundry/) and use its Gate playground with a sample JSON action.

## Try it

Open the [browser demo](https://aigovops-foundation.github.io/aigovops-policy-foundry/)
to explore without installing anything; it is static, uses bundled demo evidence
and no data leaves your device. For a local API-backed demo, start Docker Desktop
or Podman and run `./scripts/demo.sh` from the repository root. Open
`http://localhost:8000`. On Windows, run `scripts\demo.ps1`. In the dashboard,
Gate → **Try an action** accepts raw JSON. **Check on server** needs a live API
connection; the offline dashboard still evaluates its local demo. Evidence →
**Tamper with it** shows verification fail on changed demo data.

The API's interactive Swagger page is `/docs`. Open it on a running API and use
**Try it out** for routes such as `POST /api/gate/evaluate`. See the
[API reference](Pro-code-developers.md#api).

## Change configuration or prompts

You can edit `api/foundry/assets/config/agents.yaml` or files in
`api/foundry/assets/prompts/` in GitHub's web editor, then propose the change in a
pull request. CI checks policy tests and parity, API tests with OPA and without it,
web tests and build, four Terraform configurations, and a container smoke test.
These checks catch mismatches; a green run is not an approval to widen an agent's
scope.

- **Policy:** Rego format and compile, policy tests, example-policy coverage and
  generated parity golden catch policy syntax or cross-engine drift.
- **API:** pytest runs once with OPA and once with the Python fallback, catching
  route, evidence and gate regressions in both modes.
- **Web:** Vitest checks dashboard behavior; the build type-checks TypeScript and
  bundles the app.
- **Terraform:** format, initialize without a backend and validate four deployment
  examples.
- **Container:** build the image, start it with restricted privileges, then check
  health, run a pipeline and verify a downloaded bundle.

Gate behavior is different: it is defined in Rego and mirrored in Python and
TypeScript. A gate change needs Rego tests and parity corpus regeneration. Do not
make a gate-only YAML edit and assume the other engines follow it. Use Devin with
the [`foundry-gate-change` skill](../../.agents/skills/foundry-gate-change/SKILL.md)
or work with a developer.

## Paste-ready Devin prompt

```text
Read DEVIN.md and .agents/skills/foundry-gate-change/SKILL.md. Change the
capability for <agent> to <specific capability> only if the existing Rego
rules, manifest and separation-of-duties model allow it. Update tests first,
keep Rego, Python and TypeScript in parity, regenerate and explain the parity
diff, then run the relevant checks. Do not add OT reachability, secrets,
external network calls or certification claims. Stop before anything public.
Report the files changed and exact check results.
```

Use the [Hosted by Devin prompt](../../deploy/devin/README.md#prompt-to-paste-into-a-devin-session)
to propose an API and dashboard preview. Each deploy waits for human approval;
never set `FOUNDRY_DEVIN_LIVE` on a public deployment.

[Back to Home](README.md)
