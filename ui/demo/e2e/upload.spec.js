import { test, expect } from "@playwright/test";
import { authenticator } from "otplib";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Required to run (otherwise the test self-skips so it never breaks CI):
//   DEMO_E2E_EMAIL          - demo Cognito test user
//   DEMO_E2E_PASSWORD       - that user's password
//   DEMO_E2E_TOTP_SECRET    - base32 MFA shared secret captured at enrollment
// Optional:
//   DEMO_E2E_BASE_URL       - defaults to the dev server (localhost:3001)
//   DEMO_E2E_SAMPLE         - fixture path relative to this dir (default fixtures/sample.pdf)
const { DEMO_E2E_EMAIL, DEMO_E2E_PASSWORD, DEMO_E2E_TOTP_SECRET } = process.env;
const SAMPLE = process.env.DEMO_E2E_SAMPLE || "fixtures/sample.pdf";

test.describe("demo upload (real BDA)", () => {
  test.skip(
    !DEMO_E2E_EMAIL || !DEMO_E2E_PASSWORD || !DEMO_E2E_TOTP_SECRET,
    "set DEMO_E2E_EMAIL / DEMO_E2E_PASSWORD / DEMO_E2E_TOTP_SECRET to run",
  );

  test("uploads a real document and renders bounding boxes", async ({ page }) => {
    // --- Sign in (email + password) ---
    await page.goto("/");
    await page.fill("#sign-in-email", DEMO_E2E_EMAIL);
    await page.fill("#sign-in-password", DEMO_E2E_PASSWORD);
    await page.click('#sign-in-form button[type="submit"]');

    // --- MFA (TOTP) challenge: compute the same code the authenticator app would ---
    await expect(page.locator("#mfa-card")).toBeVisible();
    await page.fill("#mfa-code", authenticator.generate(DEMO_E2E_TOTP_SECRET));
    await page.click('#mfa-form button[type="submit"]');

    // --- Upload view ---
    await expect(page.locator("#demo-dropzone")).toBeVisible();
    await page.setInputFiles("#demo-file-input", path.join(__dirname, SAMPLE));
    await expect(page.locator("#demo-run-btn")).toBeEnabled();
    await page.click("#demo-run-btn");

    // --- Results: real extracted fields + real bounding boxes from BDA ---
    await expect(page.locator("#demo-results table")).toBeVisible();
    const rects = page.locator("#demo-preview-panel .bbox-overlay rect");
    await expect(rects.first()).toBeVisible();
    expect(await rects.count()).toBeGreaterThan(0);
  });
});
