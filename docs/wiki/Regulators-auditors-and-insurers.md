# Regulators, auditors and insurers

For regulators, internal audit, external assessors, brokers and carriers reviewing demo evidence.

> **Start here:** Generate a bundle, verify it offline, then change one receipt byte in a copy and verify again.

## Verify it yourself

1. In a running dashboard, open Verify. A `bundle.json` is checked on-device.
2. From a running API, download `GET /api/runs/{id}/bundle.zip`.
3. Unzip it, install Python and `cryptography` if needed, then run
   `python3 verify_bundle.py .`. The zip contains the offline verifier and its
   evidence helper; it does not need network access.
4. Copy the extracted directory, change one byte in the copied
   `receipts.ndjson`, and run the verifier again. It should report the failed
   check. Keep the original unchanged.

The dashboard can also use **Also verify on server** in live mode. For a standalone
demo bundle, use `foundry-demo --out /tmp/b --json` and `foundry-verify /tmp/b`.

## Files in a generated bundle

The API ZIP from the generated run contains `manifest.json`,
`statement.dsse.json`, `receipts.ndjson`, `checkpoint.json`,
`inclusion_bundle_signed.json`, `underwriting_packet.json`,
`devin_payloads.dryrun.json`, `pipeline_log.txt`, `foundry_evidence.py` and
`verify_bundle.py`. Its `keys/` directory has
`arbiter.ed25519.pub.hex`, `signing_officer.ed25519.pub.hex` and
`witness.ed25519.pub.hex`. Its `artifacts/` directory has
`docs/ai_code_change.md`, `policy/ai_code_change.rego`,
`tests/acceptance_test.rego`, and `reports/auditor.json` plus
`reports/verifier.json`. The CLI output with `--json` also has `bundle.json`.
Neither bundle contains private signing keys.

## What the checks establish

| Check | Establishes | Does not establish |
|---|---|---|
| Manifest | Artifact bytes match listed SHA-256 digests | That an artifact is correct |
| Statement | Two signatures verify and bind the listed subjects | That signers made a sound decision |
| Receipts | Signatures, chain links and counters verify | That every action was observed |
| Non-egress | Receipt bodies omit raw-content fields checked by the verifier | That no other system retained data |
| Checkpoint | Receipt log root and size match a witness-signed checkpoint | Independent notary service or full log completeness |
| Inclusion | The bundle-signing receipt is included and binds the statement | Policy quality, legal status or safety |
| Structure | Required bundle structure is present | Correctness of policy or runtime behavior |

These are integrity checks, not proof of completeness, policy correctness, safety,
control effectiveness or legal status. See
[assurance boundaries](../../docs/BLUEPRINT.md#151-what-this-design-does-not-prove)
and [What this is not](../../README.md#what-this-is-not).

## Underwriting evidence

The packet reports gate coverage, denial rate, human override rate, attestation
gaps, review latency, verifier distribution and incidents. Coverage is measured
against boundary-crossing actions observed in flow logs. Tier examples run from
T1 to T4; see [metrics and tiering](../../docs/BLUEPRINT.md#133-metrics-integers-in-basis-points-or-seconds).
AIUC-1 pillar coverage is self-assessed mapping, not certification.

The design touches OVERT 1.1 agentic controls, IEC 62443 zones and conduits,
AIUC-1 pillars, ISO/IEC 42001 and NIST AI RMF. These references describe mappings
and design intent; they are not endorsements, certifications or claims of
conformance.

## Questions to ask an operator

- Who controls the signing keys, and is there an independent witness?
- Does gate coverage compare receipts with flow logs, or only count receipts?
- Which actions happen inside the Devin VM and sit outside gate visibility?
- What evidence supports the requirement and each risk-tier decision?
- Who approved the policy, and who signed the exact approved bytes?

[Back to Home](README.md)
