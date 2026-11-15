# ADR 0007: Fail-closed verifier execution and bundle filesystem boundaries

- Status: **Proposed**

## Context

Uploaded manifest content is untrusted even when uploaded filenames are safe. The standalone
verifier must not read outside the extracted bundle or block on special files. Empty OPA output
is not evidence that acceptance tests passed, and a mutation tool error is not a killed mutant.

## Decision implemented for review

- Validate all manifest entries and digests before artifact/key access. Reject absolute,
  traversal and noncanonical separator forms; limit manifests to 1–1,000 entries.
- Resolve containment and reject symlink components and non-regular files for every checked
  bundle file. Bound reads cumulatively to 2,000,000 bytes, including metadata; check opened-file
  identity and bound actual reads as well as declared size. The API validates before writing
  uploaded files and counts UTF-8 bytes, not characters.
- Use real resolved containment for optional SPA delivery instead of a string-prefix test.
- Bound each verifier OPA subprocess to 30 seconds. Treat nonzero acceptance exits, malformed
  output, zero executed tests and invalid coverage/mutation runs as inconclusive errors.
  Exit 2 is expected only for mutant runs with explicit assertion failures, never tool errors.
- Abort before DSSE signing: the CLI exits nonzero; the API returns 503 and removes partial
  output without registering a run. Keep the existing explicitly labeled recorded-demo path
  when OPA is absent initially; never replay it to mask an execution failure.

## Consequences

Existing valid bundles retain the same format and signed predicate/receipt shape. Python/API
verification adds filesystem/resource restrictions; the browser verifier remains in-memory.
Large bundles or symlink-based extraction layouts are rejected. An inconclusive run must be
retried after fixing the tool problem, not interpreted as a signed policy pass. The role policy,
gate ports, privileges and parity corpus are unchanged. These remain demo evidence boundaries,
not certification or conformance claims.

## Review

- [ ] Maintainer review
