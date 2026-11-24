import { defineConfig } from "@playwright/test";

// Trailer recording config for the admin console (not part of CI, and
// not picked up by `make record-ui`, which only globs e2e-video/).
//
//   npx playwright test --config=playwright.trailer.config.js
//
// Output: video-output/<test>/*.webm (gitignored). See ../../docs/documentai-api/media/trailer/.
export default defineConfig({
  testDir: "./e2e-trailer",
  timeout: 120_000,
  reporter: [["list", { printSteps: true }]],
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
    launchOptions: { slowMo: 250 },
  },
});
