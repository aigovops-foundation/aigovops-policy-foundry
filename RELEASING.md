# Releasing

1. Open a release PR that updates `CHANGELOG.md` and the version in `api/pyproject.toml`,
   `web/package.json`, `apps/native/package.json`, `apps/native/src-tauri/Cargo.toml` and
   `apps/native/src-tauri/tauri.conf.json`.
2. CI must be green, including the container smoke test and the native build workflow.
3. Pre-release review: the Project Steward and Review Circle review the release PR. Record their
   sign-off (and any conflict-of-interest disclosures) in the PR.
4. Configure the `release` environment with required human reviewers and **Prevent self-review**.
   The publishing job checks this configuration through the GitHub API and fails before login
   if protections are missing or unreadable. This setting is an administrator prerequisite,
   not something local tests configure or verify on the hosted repository.
5. A maintainer tags `vX.Y.Z`. The `release image` workflow reruns reusable CI at the exact tag
   revision, waits for the protected environment approval, then publishes the multi-arch container to
   GHCR with SBOM and provenance. Native builds attach to the workflow run as unsigned artifacts;
   signed store builds need Apple and Google signing set up separately.
6. Never describe a release as certified or conformant. Use "OVERT-aligned" and state the
   assurance level honestly.
