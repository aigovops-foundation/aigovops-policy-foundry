# Policy Foundry persona wiki

For policy requesters, builders, developers, reviewers and people affected by governed AI changes.

> **Start here:** Pick the row that sounds like you. The Foundry is an incubating project with a local demo, not a hosted public demo.

The Policy Foundry is a reference project for governing AI-assisted policy changes.
It combines a role-boundary gate, human decisions and signed evidence.
The evidence is a demo, not proof that a policy is correct or complete.

| Your path | Who you are | First five minutes | Page |
|---|---|---|---|
| Policy and governance | Requester, owner, approver, signer, OT security or safety lead | Read REQ-1042 beside its Rego policy | [Policy and governance](Policy-and-governance.md) |
| Low-code | You edit YAML or JSON and use forms and buttons | Run the dashboard, then try a gate action | [Low-code builders](Low-code-builders.md) |
| Pro-code | You build or test Python, TypeScript or infrastructure | Install the API and run its tests | [Pro-code developers](Pro-code-developers.md) |
| Assurance | Regulator, auditor, assessor, broker or carrier | Verify a generated bundle yourself | [Regulators, auditors and insurers](Regulators-auditors-and-insurers.md) |
| End user | Plant staff or anyone whose AI-assisted change is governed | See the allow, deny and human-escalation flow | [End users](End-users.md) |

## A time ladder

- **30 seconds:** Read the [project README](../../README.md) and inspect the
  [overview screenshot](../../docs/images/overview-desktop.png).
- **5 minutes:** Run `./scripts/demo.sh` with Docker, open `http://localhost:8000`,
  then use Evidence → **Tamper with it**. On Windows, use `scripts\demo.ps1`.
- **1 hour:** Generate and verify a bundle with
  [`foundry-verify`](Regulators-auditors-and-insurers.md), or propose a rule change
  through a PR. Gate changes need Rego and regenerated parity evidence.

There is no hosted public demo today. Every persona needs Docker or Node to explore
the dashboard. The GitHub Wiki is not initialized; this in-repository wiki is the
human-written source.

## Page index

- [Policy and governance](Policy-and-governance.md)
- [Low-code builders](Low-code-builders.md)
- [Pro-code developers](Pro-code-developers.md)
- [Regulators, auditors and insurers](Regulators-auditors-and-insurers.md)
- [End users](End-users.md)
- [Devin across surfaces](Devin-across-surfaces.md)
- [Glossary](Glossary.md)
- [Make it easy: roadmap](Make-it-easy-roadmap.md)

## Questions

Open an issue in the repository's **Issues** tab. The
[DeepWiki / Ask Devin page](https://deepwiki.com/aigovops-foundation/aigovops-policy-foundry)
is available once indexed.

[Back to Home](README.md)
