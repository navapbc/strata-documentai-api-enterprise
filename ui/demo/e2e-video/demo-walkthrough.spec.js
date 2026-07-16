import { test, expect } from "@playwright/test";
import { JOB_ID, COMPLETED_DOC, previewDataUrl } from "../../shared/e2e/fixtures/recording/w2-document.js";

// ---------------------------------------------------------------------------
// Scripted, re-generatable DEMO VIDEO of the DocumentAI demo UI.
//
// This is the browser analog of a VHS terminal recording: it drives the real
// SPA (login -> upload -> extraction results with bounding-box overlay) but
// mocks EVERY network dependency (config.json, Cognito, the API) so it runs
// offline, deterministically, with no credentials or deployed infra. Playwright
// records a .webm per run (see playwright.video.config.js).
// ---------------------------------------------------------------------------

const HISTORY = {
  documents: [
    { jobId: "hist-1", fileName: "invoice-4471.pdf", processStatus: "success",
      matchedBlueprint: "Invoice", createdAt: "2026-07-16T15:10:00Z" },
    { jobId: "hist-2", fileName: "drivers-license.jpg", processStatus: "success",
      matchedBlueprint: "US Driver License", createdAt: "2026-07-16T14:30:00Z" },
    { jobId: "hist-3", fileName: "receipt-scan.png", processStatus: "no_custom_blueprint_matched",
      createdAt: "2026-07-15T22:05:00Z" },
  ],
};

// ---------------------------------------------------------------------------

test("demo walkthrough: login -> upload -> extraction with bounding boxes", async ({
  page,
}) => {
  const json = (body) => ({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(body),
  });

  // --- config.json: no Google SSO, dummy Cognito ids ------------------------
  await page.route("**/config.json", (route) =>
    route.fulfill(
      json({
        api_endpoint: { value: "https://api.demo.local" },
        cognito_user_pool_id: { value: "us-east-1_DEMO00000" },
        cognito_client_id: { value: "democlientid0000000000000" },
        cognito_domain: { value: null },
        cognito_google_enabled: { value: false },
      }),
    ),
  );

  // --- Cognito: password sign-in -> MFA challenge -> tokens -----------------
  await page.route(/cognito-idp\./, async (route) => {
    const target = route.request().headers()["x-amz-target"] || "";
    if (target.includes("InitiateAuth")) {
      return route.fulfill(
        json({ ChallengeName: "SOFTWARE_TOKEN_MFA", Session: "demo-session-token" }),
      );
    }
    if (target.includes("RespondToAuthChallenge")) {
      return route.fulfill(
        json({
          AuthenticationResult: {
            AccessToken: "demo-access-token",
            IdToken: "demo-id-token",
            RefreshToken: "demo-refresh-token",
            ExpiresIn: 3600,
          },
        }),
      );
    }
    return route.fulfill(json({}));
  });

  // --- API: history, upload, poll (started -> success), preview -------------
  let getCalls = 0;
  await page.route("**/v1/demo/documents**", async (route) => {
    const req = route.request();
    const url = req.url();

    if (req.method() === "POST") {
      return route.fulfill(json({ jobId: JOB_ID }));
    }
    if (url.includes("/preview")) {
      return route.fulfill(json({ url: previewDataUrl() }));
    }
    if (url.includes(`/documents/${JOB_ID}`)) {
      // First poll shows "Processing", second returns the finished result.
      getCalls += 1;
      if (getCalls < 2) {
        return route.fulfill(json({ jobId: JOB_ID, processStatus: "started" }));
      }
      return route.fulfill(json(COMPLETED_DOC));
    }
    // GET /v1/demo/documents -> history list
    return route.fulfill(json(HISTORY));
  });

  // === 1. Login ============================================================
  await page.goto("/");
  await expect(page.locator("#sign-in-card")).toBeVisible();
  await page.fill("#sign-in-email", "demo@example.com");
  await page.fill("#sign-in-password", "DemoPassword123!");
  await page.waitForTimeout(600);
  await page.click('#sign-in-form button[type="submit"]');

  // === 2. MFA ==============================================================
  await expect(page.locator("#mfa-card")).toBeVisible();
  await page.fill("#mfa-code", "123456");
  await page.waitForTimeout(500);
  await page.click('#mfa-form button[type="submit"]');

  // === 3. Upload view ======================================================
  await expect(page.locator("#demo-dropzone")).toBeVisible();
  await expect(page.locator("#demo-history-list .demo-history-item").first()).toBeVisible();
  await page.waitForTimeout(900);

  // Attach the sample document (a lightweight PNG buffer; contents are
  // irrelevant since the API result is mocked).
  const png = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "base64",
  );
  await page.setInputFiles("#demo-file-input", {
    name: "employee-w2-2025.png",
    mimeType: "image/png",
    buffer: png,
  });
  await expect(page.locator("#demo-run-btn")).toBeEnabled();
  await page.waitForTimeout(700);

  // === 4. Run extraction ===================================================
  await page.click("#demo-run-btn");
  await expect(page.locator("#demo-elapsed")).toBeVisible();

  // === 5. Results + bounding-box overlay ===================================
  await expect(page.locator("#demo-results table")).toBeVisible({ timeout: 30_000 });
  const rects = page.locator("#demo-preview-panel .bbox-overlay rect");
  await expect(rects.first()).toBeVisible();
  expect(await rects.count()).toBeGreaterThan(0);
  await page.waitForTimeout(1200);

  // === 6. Show the field <-> box linking (a key selling point) =============
  const rows = page.locator("#demo-results tr[data-field]");
  const n = Math.min(await rows.count(), 4);
  for (let i = 0; i < n; i++) {
    await rows.nth(i).hover();
    await page.waitForTimeout(900);
  }
  await page.waitForTimeout(1200);
});
