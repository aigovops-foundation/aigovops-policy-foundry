---
name: foundry-native-app
description: Build the Policy Foundry desktop (Windows, macOS, Linux) and mobile (Android, iOS) apps with Tauri 2.
argument-hint: <desktop|android|ios>
triggers: ["user"]
---
## Build native app: $1

The native app is `web/dist` inside a Tauri 2 shell (`apps/native`). It works offline with the
bundled demo and can connect to any Foundry API from Settings.

- desktop (on this machine's OS): `cd apps/native && npm ci && npx tauri build`
  Linux output: `src-tauri/target/release/bundle/{deb,rpm,appimage}`.
  Windows and macOS builds run in GitHub Actions (`.github/workflows/native.yml`) on their runners.
- android: install JDK 17, Android SDK + NDK 27, Rust targets
  `aarch64-linux-android armv7-linux-androideabi i686-linux-android x86_64-linux-android`, then
  `npx tauri android init --ci && npx tauri android build --apk --debug`.
- ios: needs macOS + Xcode. `npx tauri ios init --ci && npx tauri ios build --target aarch64-sim --debug`.
  Store builds need the Foundation's Apple team ID and signing set up by a human.

Do not add signing keys, store credentials or auto-update endpoints without a maintainer.
Report the artifact paths and sizes.
