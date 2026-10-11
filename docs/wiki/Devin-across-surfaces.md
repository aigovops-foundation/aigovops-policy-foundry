# Devin across surfaces

For people using Devin to understand, build, review or deploy this repository.

> **Start here:** Read [`DEVIN.md`](../../DEVIN.md) for the rules; use this page to find the right Devin surface.

The repo has two distinct uses of Devin: agents build and review this repo; the
product can make dry-run Devin v3 payloads. Live session creation is feature-flagged
and must not be enabled on public deployments.

| Surface | File or place | Purpose and status here | Owner |
|---|---|---|---|
| AGENTS.md | [`AGENTS.md`](../../AGENTS.md) | First 16 KiB are auto-loaded; keep critical rules at the top and move situational guidance to skills ([Devin guidance](https://docs.devin.ai/onboard-devin/agents-md)) | Maintainers |
| DEVIN.md | [`DEVIN.md`](../../DEVIN.md) | Build instructions, guardrails and plan | Maintainers |
| REVIEW.md | [`REVIEW.md`](../../REVIEW.md) | Devin Review reads this with AGENTS.md and CONTRIBUTING.md; `**/REVIEW.md` is supported ([Devin Review docs](https://docs.devin.ai/work-with-devin/devin-review)) | Maintainers |
| Blueprint | [`.devin/blueprint.yaml`](../../.devin/blueprint.yaml) | Linux/default and macOS documents; sync through the UI or API after merge, then build ([blueprint docs](https://docs.devin.ai/onboard-devin/environment/macos-support)) | Maintainer in Devin settings |
| DeepWiki map | [`.devin/wiki.json`](../../.devin/wiki.json) | Repo notes and the only pages generated; maximum 30 pages, 100 notes and 10,000 characters per note, with unique titles ([DeepWiki docs](https://docs.devin.ai/work-with-devin/deepwiki)) | Maintainers |
| Skills | [`.agents/skills/`](../../.agents/skills/) | Build, deploy, gate-change, verify, explain and wiki-update procedures; frontmatter can declare name, description, argument hint, tools and triggers ([skills docs](https://docs.devin.ai/product-guides/skills)) | Maintainers |
| Repo knowledge | `knowledge:` in blueprint | Repo-tier environment, test and build commands; org and enterprise tiers are configured separately | Maintainers |
| Org playbooks | Devin app, not this repo | Suggested `!foundry-build`, `!foundry-deploy`, `!foundry-verify`; a human creates them | Organization admin |
| Devin Review | Devin Review | Reads `REVIEW.md`, `AGENTS.md` and `CONTRIBUTING.md` | Review owners |
| DeepWiki / Ask Devin | DeepWiki after indexing | Uses the repo map; only listed pages are generated | Repository maintainers |
| Devin MCP + DeepWiki MCP | MCP server configuration | No repo-level server registration is included here | Organization admin |
| Devin app deployments | `deploy/devin/` | Dashboard and API preview deployment; each deploy waits for approval | Deploy operator |
| Devin v3 sessions API | `POST /api/devin/preview` | Dry-run payload only by default; live product path requires a dedicated service user with `UseDevinSessions`, `ViewOrgSessions` and `ManageOrgSessions`, `bypass_approval=false` | Product operator |

The product's live session feature additionally needs `FOUNDRY_DEVIN_LIVE=1` and a
`cog_` service-user key. It must never be enabled on a public deployment. See
[`DEVIN.md` §2](../../DEVIN.md).

## Prompt cookbook

Use specific prompts with named files and success conditions; see
[Devin's prompting guidance](https://docs.devin.ai/essential-guidelines/instructing-devin-effectively).
Do not ask Devin to cross the public boundary.

**Policy:** “Read `docs/wiki/Policy-and-governance.md`,
`api/foundry/assets/examples/req-1042/docs/ai_code_change.md` and
`api/foundry/assets/policy/role_boundaries.rego`. Draft a requirement using the
example's fields, explain which gate rules it would touch, and list open
questions. Do not edit or publish anything. Stop before anything public.”

**Low-code:** “Read `.agents/skills/foundry-gate-change/SKILL.md` and
`api/foundry/assets/config/agents.yaml`. Propose a capability change with Rego,
Python and TypeScript parity tests. Report exact check results; stop before anything public.”

**Pro-code:** “Read `CONTRIBUTING.md` and `api/app/main.py`. Add the requested
route with tests in `api/tests/test_api.py`; malformed input must not produce a
500. Run the API tests and report counts. Stop before anything public.”

**Regulator:** “Generate a bundle using `foundry-demo`, verify with
`foundry-verify` and the bundled verifier, then tamper with a copied receipt.
Report each exact check and its limits. Do not send the bundle anywhere.”

**End user:** “Read `web/src/lib/evidence.ts` and
`api/foundry/verify_bundle.py`. Explain this receipt in plain language with
file:line references. Distinguish gate integrity from policy correctness. Do not
claim certification and stop before anything public.”

[Back to Home](README.md)
