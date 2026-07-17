import { defineConfig } from "@playwright/test";

// Scripted DEMO-VIDEO config (not part of CI).
//
// Unlike e2e/upload.spec.js (which drives a LIVE API + Cognito + real BDA and
// needs credentials), this config records a self-contained, re-generatable UI
// walkthrough: every network call is mocked inside the spec, so it runs offline
// with no infra and produces a deterministic .webm per run.
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
    port: 3001,
    reuseExistingServer: true,
    stdout: "ignore",
    stderr: "pipe",
  },
  use: {
    baseURL: "http://localhost:3001",
    viewport: { width: 1280, height: 800 },
    // Record every test; size the frame to the viewport for a clean crop.
    video: { mode: "on", size: { width: 1280, height: 800 } },
    // Ease the pace so the walkthrough is watchable rather than instant.
    launchOptions: { slowMo: 600 },
  },
});
