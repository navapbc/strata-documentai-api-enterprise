import { defineConfig } from "@playwright/test";

// Scripted DEMO-VIDEO config for the admin console (not part of CI).
//
// Mocks every network call inside the spec so it runs offline with no infra
// and produces a deterministic .webm per run.
//
//   npm run dev  (or let webServer start it) then:
//   npx playwright test --config=playwright.video.config.js
//
// Output: video-output/<test>/*.webm  ->  convert to GIF with ../shared/scripts/webm-to-gif.sh
export default defineConfig({
  testDir: "./e2e-video",
  timeout: 120_000,
  outputDir: "./video-output",
  webServer: {
    command: "npm run dev",
    port: 3000,
    reuseExistingServer: true,
    stdout: "ignore",
    stderr: "pipe",
  },
  use: {
    baseURL: "http://localhost:3000",
    viewport: { width: 1280, height: 800 },
    video: { mode: "on", size: { width: 1280, height: 800 } },
    launchOptions: { slowMo: 600 },
  },
});
