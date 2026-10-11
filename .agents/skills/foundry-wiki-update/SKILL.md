---
name: foundry-wiki-update
description: Keep persona guidance and the DeepWiki page map aligned with user-facing behavior changes.
triggers: [user, model]
---

## Update the persona wiki

1. Read `DEVIN.md`, `REVIEW.md` and the relevant source and tests. Confirm the
   changed behavior exists before describing it.
2. Update the relevant page under `docs/wiki/`. Keep each page below 200 lines,
   include a Home link, and use relative links for repository content.
3. Update `.devin/wiki.json` when page titles, purposes or persona paths change.
   Keep repo notes at three or fewer; titles must be unique and pages below 30.
4. Check every claim for the approved language: OVERT-aligned, self-assessed or
   demo evidence. Do not imply certification or conformance.
5. Run `python3 scripts/check_docs.py` and fix broken links, anchors or map limits.
   The checker is not wired into CI by default.
6. Report the pages updated and exact checker output.
