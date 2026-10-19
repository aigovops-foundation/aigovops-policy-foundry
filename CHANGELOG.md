# Changelog

## 0.1.0 (unreleased, incubating)

- Group Dependabot updates into one pull request per ecosystem per interval (weekly on Monday for
  GitHub Actions, npm and pip; monthly for cargo and docker) instead of one PR per package.
- Container image moves to the estate's two standard bases: the web build stage on `node:22-alpine`
  (was `node:22-bookworm-slim`) and the runtime on `python:3.12-slim` (was `python:3.14-slim-bookworm`,
  which CI never tested; `requires-python >= 3.11`).
- Add the persona wiki, DeepWiki page map, Devin review guidance and skills, macOS blueprint,
  policy request form, and documentation link checker.
- Publish the static dashboard demo to GitHub Pages with bundled demo evidence only.
- Add a Start here role picker (shareable `#/start/<role>` links) and a Policy page that shows the plain-language policy, its rule and tests, and who approved and signed, all from the signed bundle.
- Fix dashboard accessibility issues found by axe (receipt list semantics, keyboard-scrollable code panes, warning-pill contrast) and add social preview tags.
- Add the 90-second demo walkthrough and dashboard demo-testing notes to foundry-build.
- Governed four-agent policy pipeline (manager, policy writer, test verifier, compliance auditor)
  with a Rego role-boundary gate, separation-of-duties checks, signed hash-chained receipts, an
  RFC 6962 Merkle checkpoint, DSSE dual-signed bundles and an offline verifier.
- FastAPI service, React dashboard with on-device verification, Tauri desktop and mobile shell.
- Hosting: local container (macOS, Windows, Linux), Google Cloud Run (default), Azure Container
  Apps, AWS ECS Fargate, Kubernetes, Fly.io, and Devin app deployments.
- Gate parity corpus (1,005 decisions, 28 approval sets) holding OPA, Python and TypeScript to the
  same answers.
- Security fix before first release: the Rego gate failed open when a delegation omitted
  `parent_scope`, and relied on a fallback rule when the delegating agent had no `may_delegate_to`
  or the target agent was unknown. Found by the parity corpus; now fails closed with regression tests.
