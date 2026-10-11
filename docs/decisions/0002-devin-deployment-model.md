# ADR 0002: Devin deployment model for enterprise use (blueprint decision D1)

- Status: **Proposed**
- Date: 2026-10-11

## Context
The gate sees actions that cross customer conduits, not shell commands inside a Devin VM.
Devin's Customer Dedicated Deployment connects over AWS PrivateLink; Devin Outposts run Devin's
machines on customer-controlled infrastructure.

## Options
1. Customer Dedicated Deployment + PrivateLink, gate at every conduit (current blueprint).
2. Evaluate Outposts for in-VM coverage, keeping the same gate.

## Proposal
Start with option 1 for pilots; run a time-boxed evaluation of option 2 and record findings here.

## Agreed by
- [ ] Maintainers  - [ ] Customer security architect (per deployment)
