import { defineConfig } from "@playwright/test";

// Trailer recording config for the demo UI (not part of CI, and not
// picked up by `make record-ui`, which only globs e2e-video/).
//
//   npx playwright test --config=playwright.trailer.config.js
//
// Output: video-output/<test>/*.webm (gitignored). See ../../docs/documentai-api/media/trailer/.
// Full-HD frames keep text legible after the clips are scaled and captioned.
export default defineConfig({
  testDir: "./e2e-trailer",
  timeout: 120_000,
  outputDir: "./video-output",
  webServer: {
    command: "npm run dev",
    port: 3001,
    reuseExistingServer: true,
    stdout: "ignore",
    stderr: "pipe",
  },
  use: {
    baseURL: "http://localhost:3001",
    viewport: { width: 1280, height: 800 },
    video: { mode: "on", size: { width: 1280, height: 800 } },
    // Lighter than the GIF walkthroughs (600); pacing is set by explicit waits.
    launchOptions: { slowMo: 250 },
  },
});
