# Security

## Reporting a vulnerability

Email **security@aigovops-foundation.com**, or open a private security advisory on GitHub.
Please do not file public issues for unpatched vulnerabilities.

- Acknowledgement: within 2 business days.
- Triage and severity assessment: within 5 business days.
- Fix or mitigation: depending on severity, within 14 to 60 days.

We credit reporters in the release notes unless you ask us not to.

## What this project protects

- Tamper-evidence of receipts and bundles: Ed25519 signatures over RFC 8785 canonical bytes,
  hash-chained receipts with contiguous counters, an RFC 6962 Merkle tree and a witness-signed
  checkpoint, and DSSE envelopes that need two signatures.
- Role boundaries: the gate denies or escalates out-of-scope agent actions and fails closed on
  missing fields. OPA, the Python port and the TypeScript port are held together by a 1,000+ case
  parity corpus in CI.
- Non-egress: receipts carry keyed commitments and digests, not prompts, content or identities.

## What it does not protect

- Anything if a signing key is exfiltrated. The demo generates throwaway keys per run. Production
  keys belong in a KMS or HSM with MFA-gated use (see docs/BLUEPRINT.md section 11).
- Actions inside a Devin VM that never cross a gated conduit.
- The correctness, completeness or legality of a generated policy. Signatures prove who signed
  which bytes, not that the bytes are right.

## Hard rules for deployments

- The demo API has no user accounts. Set `FOUNDRY_API_TOKEN` and put SSO in front of any
  non-local deployment. The local compose file binds to 127.0.0.1 only.
- Never enable live Devin calls (`FOUNDRY_DEVIN_LIVE=1`) from a public deployment. The public API
  only builds dry-run payloads.
- Rotate signing keys at least every 90 days and record the rotation as a receipt.
