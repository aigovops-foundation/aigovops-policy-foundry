# Policy Foundry native apps (Tauri 2)

One codebase (`web/`) wrapped for **Windows, macOS, Linux, Android and iOS**. The apps work offline
with bundled demo evidence and verify bundles on-device. Connect any Foundry API from Settings.

```sh
cd apps/native && npm ci
npx tauri dev                 # desktop dev window (starts the web dev server)
npx tauri build               # installer/bundle for the current OS
npx tauri android init --ci && npx tauri android build --apk --debug
npx tauri ios init --ci && npx tauri ios build --target aarch64-sim --debug   # macOS + Xcode
```

Prerequisites: https://v2.tauri.app/start/prerequisites/ (Rust; WebKitGTK on Linux; WebView2 on
Windows, preinstalled on 10/11; Xcode for macOS/iOS; JDK 17 + Android SDK/NDK for Android).

CI builds unsigned artifacts for all five platforms in `.github/workflows/native.yml`. Store
distribution needs Foundation-owned signing credentials and Review Circle sign-off.

PR validation includes `web/**` as well as the shell/workflow, since native apps consume
the shared dashboard. Simulator CI always uses a placeholder team, not signing secrets.
Normal native builds fetch npm dependencies through `beforeBuildCommand` and may fetch
Rust/platform dependencies. They are not hermetic offline checks by default.

For a prepared-cache desktop check, first install platform prerequisites and explicitly
prepare dependencies while network access is allowed: run `npm ci` in both `web` and
`apps/native`, and `cargo fetch --manifest-path apps/native/src-tauri/Cargo.toml` from
the repo root. Preserve that toolchain, Cargo cache/lock and both node_modules trees.
Then build the web assets (`cd web && npm run build`) and, from `apps/native`, use:

```sh
npx --offline tauri build --no-bundle --no-sign --config '{"build":{"beforeBuildCommand":""}}' -- --offline
```

This bypasses the network-installing hook and fails on missing cached crates/tools;
it does not provision mobile SDKs or establish device behavior. Run it only on a prepared
host. The omnibus web/API verification does not claim this native build was executed.

Identifier: `com.aigovopsfoundation.policyfoundry`. Icons: regenerate with `npm run icons` from
`app-icon.png`.
