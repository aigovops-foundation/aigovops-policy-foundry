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

Identifier: `com.aigovopsfoundation.policyfoundry`. Icons: regenerate with `npm run icons` from
`app-icon.png`.
