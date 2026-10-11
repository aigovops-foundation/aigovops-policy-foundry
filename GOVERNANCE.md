# How decisions are made

This project follows the AiGovOps Foundation's community governance, written down in plain language
in the Foundation's project repositories (see
[aigovops-beacon/GOVERNANCE.md](https://github.com/aigovops-foundation/aigovops-beacon/blob/main/GOVERNANCE.md)).
The short version for this repo:

- **The people who pay for the project do not decide what the project is.** Technical governance
  (maintainers, the Project Steward and the Review Circle) is separate from business governance
  (the Foundation's board, off-repo).
- **The repo is the source of truth.** Decisions that matter land as PRs or ADRs in
  [`docs/decisions/`](docs/decisions/).
- **Pre-release review.** No release ships until the Project Steward and the Review Circle have
  looked at it. See [`RELEASING.md`](RELEASING.md).
- **We implement standards; we do not issue them.** This project consumes OVERT and Beacon. Changes
  to OVERT go to the standard's own process.
- **No certification, ever.** Outputs are evidence for humans, assessors and underwriters to judge.
- **Conflicts of interest are disclosed** by anyone reviewing releases.

## Project status

**Incubating.** Version 0.1.0 is a reference implementation and demo. It has not passed Review
Circle pre-release review yet. ADR 0001 records the proposal to create the project.
