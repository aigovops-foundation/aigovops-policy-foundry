# ADR 0006: AIUC-1 control mapping and predicate type ownership (blueprint decisions D5, D7)

- Status: **Proposed**
- Date: 2026-10-11

## Context
Mapping to specific AIUC-1 control IDs needs a licensed control snapshot. The bundle uses a
proposed in-toto predicate type `https://aigovops.foundation/foundry/policy-artifact/v0.1`.

## Proposal
- Map to AIUC-1 pillars only (self-assessed) until a licensed snapshot is available.
- Keep the predicate type in this repo's schema folder as v0.1; propose folding it into Beacon's
  evidence vocabulary once Beacon's profile is registered.

## Agreed by
- [ ] Maintainers  - [ ] Beacon maintainers
