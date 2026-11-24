import { mkdirSync, writeFileSync } from "node:fs";
import { test, expect } from "@playwright/test";
import {
  JOB_ID,
  COMPLETED_DOC,
  previewDataUrl,
} from "../../shared/e2e/fixtures/recording/pay-stub-document.js";
import { hoverFields, expectBboxOverlay } from "../../shared/e2e/helpers/document-viewer.js";

// ---------------------------------------------------------------------------
// Trailer, clip 1 (narration beats 1-2, ~25s once retimed):
//   upload a synthetic pay stub -> extracted fields beside the source document
//   -> inspect the flagged (low-confidence) field.
//
// Like e2e-video/, every network dependency is mocked so this runs offline and
// deterministically. It lives in e2e-trailer/ (not e2e-video/) so that
// `make record-ui` does not pick it up and write GIFs into docs/.../media/walkthroughs.
// Record with: npx playwright test --config=playwright.trailer.config.js
// The docs/documentai-api/media/trailer/ folder assembles the clips.
// ---------------------------------------------------------------------------

const HISTORY = {
  documents: [
    {
      jobId: "hist-1",
      fileName: "pay-stub-oct-2026.pdf",
      processStatus: "success",
      matchedBlueprint: "Pay Stub",
      createdAt: "2026-11-05T15:10:00Z",
    },
    {
      jobId: "hist-2",
      fileName: "employment-letter.pdf",
      processStatus: "success",
      matchedBlueprint: "Employment Verification",
      createdAt: "2026-11-04T14:30:00Z",
    },
    {
      jobId: "hist-3",
      fileName: "bank-statement.png",
      processStatus: "no_custom_blueprint_matched",
      createdAt: "2026-11-03T22:05:00Z",
    },
  ],
};

test("trailer demo: upload pay stub -> fields beside source -> flagged field", async ({ page }) => {
  const startedAt = Date.now();
  const json = (body) => ({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(body),
  });

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

  let getCalls = 0;
  let uploaded = false;
  await page.route("**/v1/demo/documents**", async (route) => {
    const req = route.request();
    const url = req.url();
    if (req.method() === "POST") {
      uploaded = true;
      return route.fulfill(json({ jobId: JOB_ID }));
    }
    if (url.includes("/preview")) {
      return route.fulfill(json({ url: previewDataUrl() }));
    }
    if (url.includes(`/documents/${JOB_ID}`)) {
      // One "Processing" poll (the UI polls every 3s), then the result: about 6s
      // of visible processing. The assembler labels any speed-up of this stretch.
      getCalls += 1;
      if (getCalls < 2) {
        return route.fulfill(json({ jobId: JOB_ID, processStatus: "started" }));
      }
      return route.fulfill(json(COMPLETED_DOC));
    }
    const docs = uploaded
      ? [
          {
            jobId: JOB_ID,
            fileName: "pay-stub-nov-2026.png",
            processStatus: "success",
            matchedBlueprint: "Pay Stub",
            createdAt: new Date().toISOString(),
          },
          ...HISTORY.documents,
        ]
      : HISTORY.documents;
    return route.fulfill(json({ ...HISTORY, documents: docs }));
  });

  // PNG/PDF/JPEG uploads go through a presigned S3 POST (see services/documents.js).
  // Registered after the generic route above, so it takes precedence.
  await page.route("**/v1/demo/documents/presigned-url", (route) =>
    route.fulfill(
      json({
        uploadUrl: "https://s3.demo.local/upload",
        fields: { key: `uploads/${JOB_ID}` },
        jobId: JOB_ID,
      }),
    ),
  );
  await page.route("https://s3.demo.local/**", (route) => route.fulfill({ status: 204, body: "" }));

  // --- Beat 1: sign in, upload a synthetic pay stub -------------------------
  const payload = btoa(JSON.stringify({ "cognito:groups": [], email: "demo@example.com" }));
  await page.goto("/");
  await page.evaluate(() => sessionStorage.clear());
  await page.goto("/");
  await page.locator("#sign-in-email").fill("demo@example.com");
  await page.locator("#sign-in-password").fill("••••••••••••");
  await page.evaluate((p) => {
    sessionStorage.setItem(
      "documentai_console_session",
      JSON.stringify({
        accessToken: "fake-at",
        idToken: `h.${p}.s`,
        refreshToken: "fake-rt",
        email: "demo@example.com",
        expiresAt: Date.now() + 3600000,
      }),
    );
  }, payload);
  await page.goto("/");

  await expect(page.locator("#demo-dropzone")).toBeVisible();
  await expect(page.locator("#demo-history-list .demo-history-item").first()).toBeVisible();
  // The upload screen is ready here. The assembler holds this frame under the
  // overview narration and plays the real action from this point.
  const readyAt = (Date.now() - startedAt) / 1000;
  await page.waitForTimeout(700);

  // Contents are irrelevant: the API result is mocked.
  const png = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "base64",
  );
  await page.setInputFiles("#demo-file-input", {
    name: "pay-stub-nov-2026.png",
    mimeType: "image/png",
    buffer: png,
  });
  await expect(page.locator("#demo-run-btn")).toBeEnabled();
  await page.waitForTimeout(700);
  await page.click("#demo-run-btn");
  await page.mouse.move(0, 0);
  await expect(page.locator("#demo-elapsed")).toBeVisible();

  // --- Beat 2: fields beside the source document, then the flagged field ----
  // The results panel holds several tables (overview, processing, fields).
  await expect(page.locator("#demo-results tr[data-field]").first()).toBeVisible({
    timeout: 30_000,
  });
  // Save when results appeared so the assembler can retime the two halves
  // (upload + processing vs results) to separate narration beats. The video
  // starts at context creation, slightly before this test body.
  mkdirSync("video-output", { recursive: true });
  writeFileSync(
    "video-output/trailer-demo-marks.json",
    JSON.stringify({ readyAtSec: readyAt, resultsAtSec: (Date.now() - startedAt) / 1000 }),
  );
  await expectBboxOverlay(page, expect, "#demo-preview-panel .bbox-overlay rect");
  await page.waitForTimeout(2500);

  // Confident fields first while the narration explains the value-to-box link,
  // then the flagged employee ID last, matching the "low-confidence fields are
  // flagged" sentence that closes the beat.
  const names = ["grossPay", "payPeriod", "netPay", "employeeId"];
  await hoverFields(page, names, "#demo-results tr[data-field]", 1800);
  await page.waitForTimeout(1500);
});
