# Releasing

1. Open a release PR that updates `CHANGELOG.md` and the version in `api/pyproject.toml`,
   `web/package.json`, `apps/native/package.json`, `apps/native/src-tauri/Cargo.toml` and
   `apps/native/src-tauri/tauri.conf.json`.
2. CI must be green, including the container smoke test and the native build workflow.
3. Pre-release review: the Project Steward and Review Circle review the release PR. Record their
   sign-off (and any conflict-of-interest disclosures) in the PR.
4. A maintainer tags `vX.Y.Z`. The `release image` workflow publishes the multi-arch container to
   GHCR with SBOM and provenance. Native builds attach to the workflow run as unsigned artifacts;
   signed store builds need Apple and Google signing set up separately.
5. Never describe a release as certified or conformant. Use "OVERT-aligned" and state the
   assurance level honestly.
