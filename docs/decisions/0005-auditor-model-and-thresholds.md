# ADR 0005: Auditor model family and quality thresholds (blueprint decisions D4, D6)

- Status: **Proposed**
- Date: 2026-10-11

## Proposal
- The Compliance Auditor must run on a different model family and runtime from the Policy Writer.
  Pin model versions per deployment and record them in `session_open`.
- Thresholds: rule coverage >= 9000 bp, mutation score >= 8000 bp, at most 4 iterations, 48-hour
  approval timeout (attested as denial), reviewer fatigue cap 2 approvals/minute.

## Agreed by
- [ ] Maintainers  - [ ] Governance Board of each adopting organisation (thresholds are per deployment)
