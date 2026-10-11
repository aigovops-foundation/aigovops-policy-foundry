# Make it easy: roadmap

For maintainers deciding what would help each persona take a safe next step.

> **Start here:** The public demo, new access and releases need human approval; this page separates shipped work from proposals.

Effort is a rough estimate. “Approval” names who must decide before the work crosses
an access or public boundary.

| Priority | What | Why / persona | Effort | Human approval? |
|---|---|---|---|---|
| 1 | Publish the offline dashboard on GitHub Pages | Let every persona explore without Docker. Vite already uses `base: "./"`; a maintainer must enable Pages and approve a public URL under DEVIN.md guardrail 7. **Not done.** | M | Yes — maintainer |
| 2 | Policy request issue form | Give policy owners a structured intake path. **Done in this PR.** | S | No for code; maintainer creates the `policy-request` repository label if needed |
| 3 | Printable approval packet and plain-language policy export | Help approvers and signers review the same material. **Not done.** | M | Yes — governance owner |
| 4 | Devcontainer or Codespaces setup | Reduce setup friction for pro-code developers. **Not done.** | M | Yes — maintainer before public image / Codespaces policy |
| 5 | Single-file verifier download and `pipx run` | Make offline verification easier for regulators. **Not done.** | M | No for code; yes before publishing a download |
| 6 | Guided persona tours in the dashboard | Explain the demo to low-code builders and end users. **Not done.** | M | No |
| 7 | Spanish locale | Meet the estate's EN/ES standard for users. **Not done.** | L | Yes — language reviewer |
| 8 | Register org playbooks with `!foundry-build`, `!foundry-deploy` and `!foundry-verify` macros | Make repeatable operations available in Devin. **Not done.** | S | Yes — org administrator creates playbooks |
| 9 | DeepWiki indexing and badge | Improve discoverability after the human-written page map is indexed. **Map added in this PR; indexing not done.** | S | Yes — maintainer enables / approves indexing |
| 10 | Screen-reader pass | Check real assistive technology; DEVIN.md says this has not been done. **Not done.** | M | No |
| 11 | Add the docs link checker to CI | Catch broken relative links and wiki-map limits on future changes. **Script added in this PR; CI wiring intentionally not done.** | S | Yes — maintainer review |

The [persona wiki](README.md) and Devin surfaces, blueprint and policy request
form are included in this PR. No hosted demo, public artifact, org playbook or
account configuration is created here.

[Back to Home](README.md)
