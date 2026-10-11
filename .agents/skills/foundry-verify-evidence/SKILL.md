---
name: foundry-verify-evidence
description: Generate a Foundry bundle, verify it independently and demonstrate which check catches tampering.
argument-hint: [output-directory]
triggers: [user, model]
---

## Verify a bundle

1. Read `DEVIN.md` guardrails and `docs/wiki/Regulators-auditors-and-insurers.md`.
2. Generate a bundle with `foundry-demo --out <directory> --json`, then run
   `foundry-verify <directory>`. Keep the output and record each named check.
3. Start the API locally, create a demo run with `POST /api/runs`, download
   `/api/runs/{id}/bundle.zip`, and extract it into a separate directory.
   Stop the local server when finished.
4. Run the extracted bundle's `python3 verify_bundle.py .`. Compare its named
   checks with the CLI result. Do not upload the bundle.
5. Copy the extracted directory. In the copy only, change one byte in a receipt
   while keeping the file readable. Run the bundled verifier and capture the
   failed check name and output. A nonzero exit is expected.
6. Report paths to both bundles, exact pass/fail checks and the limits of what
   verification establishes. Never describe a passing bundle as proof of policy
   correctness, completeness or safety.
