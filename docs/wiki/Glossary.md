# Glossary

For anyone reading a policy, receipt, bundle or assurance report.

> **Start here:** A passing verifier checks specific evidence properties; it does not decide whether a policy is right.

| Term | Meaning here |
|---|---|
| Gate | Role-boundary policy check for actions crossing observed system boundaries. |
| Receipt | Signed record of an observed action or event; demo receipts avoid raw payloads. |
| Receipt log | Ordered receipt sequence with signatures, counters and previous-record links. |
| Hash chain | Each receipt is linked to prior evidence so edits or gaps can be detected. |
| Merkle checkpoint | A compact root representing the receipt log and its size. |
| Witness | Key that signs the checkpoint in this demo; it is not an independent notary service. |
| Bundle | Policy artifacts, reports and evidence files bound by a signed statement, with a verifier. |
| DSSE | Envelope format carrying a payload and signatures; this bundle wraps an in-toto statement. |
| in-toto statement | Attestation statement naming the subjects whose digests are signed. |
| Keyed commitment | A digest made with a secret key to bind data without exposing its raw value. |
| Parity corpus | Cases used to compare OPA, Python and TypeScript gate answers. |
| Mutation score | Share of deliberately changed rules caught by tests. |
| Basis point (bp) | One hundredth of a percent; 10,000 bp is 100%. |
| AAL | OVERT assurance-level shorthand; the demo is operator-signed and does not claim AAL-4. |
| OVERT | Open standard for verifying AI safeguards, from Glacis (shared stewardship with CHAI and AiGovOps announced; see [BLUEPRINT §3](../../docs/BLUEPRINT.md#3-standards-and-platform-baseline-verified-october-2026)). Mappings here are self-assessed; receipts are OVERT-aligned, not a registered profile. |
| Beacon | AiGovOps Foundation's OVERT 1.0 receipt and gate runtime; the Foundry keeps receipts compatible with Beacon's JSON path. |
| HITL | Human-in-the-loop review or decision. |
| Separation of duties | Distinct identities perform requesting, approving and signing. |
| OT | Operational technology, such as plant-floor control systems. |
| Conduit / zone | A controlled network path / a grouped security boundary in an OT design. |
| Review Circle | Human release review described by the Foundation release process. |
| ADR | Architecture Decision Record that records a proposal or accepted decision. |

[Back to Home](README.md)
