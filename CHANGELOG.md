# Changelog

## 0.1.0 (unreleased, incubating)

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
