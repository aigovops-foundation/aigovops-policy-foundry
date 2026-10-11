# ADR 0001: Create the AiGovOps Policy Foundry as an incubating project

- Status: **Proposed** (awaiting maintainer and Review Circle review)
- Date: 2026-10-11
- Proposed by: Bob Rapp

## Context
Manufacturers adopting AI coding agents need governance policies that are executable, tested and
verifiable, and insurers increasingly ask for evidence that agents are governed. The Foundation
already maintains Beacon (verifiable evidence) and Lantern (human-readable view) and implements
OVERT. There was no reference showing a governed multi-agent system that produces signed policy
artifacts end to end.

## Decision
Create `aigovops-policy-foundry` as an incubating Foundation project: a reference implementation
and demo of a Devin-backed, four-agent policy pipeline with a role-boundary gate, OVERT-aligned
receipts, dual-signed bundles, an offline verifier, an underwriting evidence packet, a dashboard,
an API and native apps.

## Consequences
- The project consumes Beacon and OVERT; it does not change either. Receipt format alignment with
  Beacon is tracked in ADR 0003.
- No certification or conformance claims. Status stays "incubating" until Review Circle sign-off.
- Releases follow `RELEASING.md`. The container image is published only on a maintainer-pushed tag.

## Agreed by
- [ ] Bob Rapp (maintainer)
- [ ] Ken Johnston (maintainer)
- [ ] Project Steward / Review Circle
