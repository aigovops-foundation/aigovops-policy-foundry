# ADR 0003: Receipt profile (blueprint decision D2)

- Status: **Proposed**
- Date: 2026-10-11

## Context
Foundry receipts are a JSON profile (RFC 8785 + Ed25519), matching Beacon today. OVERT Protocol
Profile 1.0's base envelope is deterministic CBOR. OVERT 1.1 is current; Beacon cites 1.0.

## Proposal
Keep the JSON profile and describe receipts as "OVERT-aligned" until Beacon's profile registration
lands. Then align field-for-field with Beacon's registered profile, with a migration note.
Talk to the Project Steward before any schema change.

## Agreed by
- [ ] Maintainers  - [ ] Project Steward
