// The app is the same web dashboard (web/dist) in a native window. It works offline with the
// bundled demo evidence and verifies bundles on-device; it can also connect to any Foundry API.
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .run(tauri::generate_context!())
        .expect("error while running Policy Foundry");
}
