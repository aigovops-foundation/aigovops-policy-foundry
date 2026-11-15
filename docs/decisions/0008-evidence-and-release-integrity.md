# ADR 0008: Packet integrity and release boundaries

Status: Proposed for maintainer review.

## Context

The underwriting packet already has a canonical SHA-256 commitment in a signed
receipt, but neither verifier compared it. Malformed runtime JSON could escape
TypeScript types or become API exceptions. Tagged publication lacked a CI dependency.

## Decision

Both verifiers validate consumed runtime structures and require exactly one
`underwriting_packet` receipt after the proven `bundle_signed` receipt. Its digest
must match canonical packet bytes; the receipt chain and witnessed checkpoint must
verify. The dashboard suppresses unverified packet metrics. Existing bundle, receipt
and DSSE formats are unchanged, including the committed demo's packet commitment.

Gate ports follow unchanged authoritative Rego on the extended parity corpus,
including presence semantics for empty/null/malformed delegations. Nonempty scoped
delegations without a target remain invalid: the editor rejects them and ports retain
their prior deny, rather than introducing an allow for an out-of-contract object.
Added corpus cases do not change existing decisions or capabilities.

Credentials remain in memory, scoped to a normalized API destination (including its
path). Switching destinations or selecting offline clears them and any HTTP consent.
Remote plaintext HTTP requires explicit token consent; authenticated fetches reject
redirects. Verify actions share the displayed selection and discard stale responses.

Tagged publication calls CI at the tagged revision, then uses a protected `release`
environment. A pre-publication API check fails closed without required independent
reviewers, including when that protection configuration cannot be read. Repository
administrators must configure reviewers and prohibit self-review before publication.
No release, environment mutation, signing or deployment is performed by this change.

Native PR validation includes the shared web source. CI uses a placeholder team for
unsigned simulator builds; native/device/store signing remains separate and human-owned.

## Limits

Demo integrity is not policy correctness, completeness, control effectiveness or
legal status. Public keys shipped in the same bundle are not an independently
trusted identity root. A local passing test does not prove hosted or native builds pass.

[Home](../wiki/README.md)
