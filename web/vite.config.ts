import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// base "./" so the same build works on any static host, devinapps.com, the API container,
// and inside Tauri desktop/mobile webviews.
export default defineConfig({
  base: "./",
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://localhost:8000", "/healthz": "http://localhost:8000" } },
  build: { target: "es2022", sourcemap: false, chunkSizeWarningLimit: 900 },
  test: { environment: "node" },
});
