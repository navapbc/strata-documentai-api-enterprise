import { defineConfig } from "@playwright/test";

// Real-backend e2e: drives the demo UI against a live API (config.json endpoint),
// uploads a real document, and asserts BDA-extracted bounding boxes render.
// Gated to manual/nightly runs - it hits live BDA, so it's not part of per-PR CI.
export default defineConfig({
  testDir: "./e2e",
  // BDA processing dominates wall-clock; keep generous.
  timeout: 180_000,
  expect: { timeout: 150_000 },
  // The dev server serves the SPA; it talks to the real API via config.json.
  webServer: {
    command: "npm run dev",
    port: 3001,
    reuseExistingServer: true,
  },
  use: {
    baseURL: process.env.DEMO_E2E_BASE_URL || "http://localhost:3001",
    trace: "on-first-retry",
  },
});
