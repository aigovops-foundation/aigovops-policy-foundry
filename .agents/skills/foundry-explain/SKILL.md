---
name: foundry-explain
description: Answer read-only policy and end-user questions using precise repository references and careful claims.
allowed-tools: [read, grep]
triggers: [user, model]
---

## Explain the Foundry

1. Read `docs/wiki/README.md` and the persona page closest to the question.
2. Use only repository reading and text search. Do not edit files, run actions or
   call external services.
3. Check behavior against source code, schemas or tests. Give file-and-line
   references for each important claim.
4. Use plain language. Separate observed gate behavior from policy correctness
   and from what evidence does not establish.
5. Do not claim certification or conformance. Prefer "OVERT-aligned",
   "self-assessed" or "demo evidence" when accurate.
6. If the feature does not exist, say so and point to
   `docs/wiki/Make-it-easy-roadmap.md`. Do not invent a path or capability.
