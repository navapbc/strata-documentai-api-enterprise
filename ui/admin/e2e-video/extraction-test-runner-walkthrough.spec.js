import { test, expect } from "@playwright/test";
import {
  JOB_ID,
  TENANT_ID,
  COMPLETED_DOC,
  previewDataUrl,
} from "../../shared/e2e/fixtures/recording/passport-document.js";
import { registerConfig, registerTenants, loginAs } from "../../shared/e2e/helpers/routes.js";
// ---------------------------------------------------------------------------
// Scripted demo video: Extraction Test Runner walkthrough.
//
// Flow: start logged in -> Extraction Test Runner -> select tenant -> drop file
//       -> run -> result renders with extracted fields
// All network dependencies are mocked - runs offline, no credentials needed.
// ---------------------------------------------------------------------------

const TENANTS = [
  { tenantId: TENANT_ID, displayName: "Acme Corporation", isActive: true },
  { tenantId: "river-health", displayName: "River Health Systems", isActive: true },
];

const HISTORY_DOC = {
  jobId: "prev-run-0001",
  fileName: "drivers-license.jpg",
  processStatus: "success",
  tenantId: TENANT_ID,
  createdAt: "2026-10-21T18:00:00Z",
};

test("extraction test runner walkthrough", async ({ page }) => {
  const json = (body) => ({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(body),
  });

  // --- config.json ----------------------------------------------------------
  registerConfig(page);

  // --- tenants --------------------------------------------------------------
  registerTenants(page, TENANTS);

  // --- extraction test: POST -> jobId, GET poll -> completed ----------------
  await page.route("**/v1/admin/extraction-test", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill(json({ jobId: JOB_ID }));
    }
    route.continue();
  });
  await page.route(`**/v1/admin/extraction-test/${JOB_ID}**`, (route) =>
    route.fulfill(json({ jobId: JOB_ID, isCompleted: true, isFailed: false })),
  );

  // --- documents: history list, enriched result, preview -------------------
  await page.route("**/v1/admin/documents**", (route) => {
    const url = route.request().url();
    if (url.includes(`/documents/${JOB_ID}/preview`)) {
      return route.fulfill(json({ url: previewDataUrl() }));
    }
    if (url.includes(`/documents/${JOB_ID}`)) {
      return route.fulfill(json(COMPLETED_DOC));
    }
    // history list (isTestRun=true)
    return route.fulfill(json({ documents: [HISTORY_DOC], cursor: null }));
  });

  // --- other routes the shell may call on load ------------------------------
  await page.route("**/v1/admin/api-keys**", (route) =>
    route.fulfill(json({ keys: [] })),
  );
  await page.route("**/v1/dictionary/**", (route) =>
    route.fulfill(json({ fields: [] })),
  );

  // === 1. Start logged in ==================================================
  await test.step("Start logged in", async () => {
    await loginAs(page);
    await expect(page.locator("#view-title")).toHaveText("Home");
  });

  // === 2. Navigate to Extraction Test Runner ================================
  await test.step("Navigate to Extraction Test Runner", async () => {
    await expect(page.locator("#view-title")).toHaveText("Home");
    await page.locator('[data-section="qa-tools"]').click();
    await expect(page.locator("#section-qa-tools")).not.toHaveClass(/hidden/);
    await page.locator('a.nav-item[data-view="extraction-test-runner"]').click();
    await expect(page.locator("#view-title")).toHaveText("Extraction Test Runner");
    await expect(page.locator("#extraction-test-empty")).toBeVisible();
    await page.waitForTimeout(800);
  });

  // === 3. Select tenant =====================================================
  await test.step("Select tenant", async () => {
    await page.locator("#tenant-select").selectOption(TENANT_ID);
    await expect(page.locator("#extraction-test-history .doc-list-item").first()).toBeVisible();
    await page.waitForTimeout(900);
  });

  // === 4. Drop file =========================================================
  await test.step("Drop file", async () => {
    await page.locator("#extraction-test-file").setInputFiles({
      name: "us-passport.jpg",
      mimeType: "image/jpeg",
      buffer: Buffer.from("x"),
    });
    await expect(page.locator("#extraction-test-dropzone-selected")).not.toHaveClass(/hidden/);
    await expect(page.locator("#extraction-test-file-name")).toHaveText("us-passport.jpg");
    await expect(page.locator("#extraction-test-run-btn")).toBeEnabled();
    await page.waitForTimeout(900);
  });

  // === 5. Run extraction ====================================================
  await test.step("Run extraction", async () => {
    await page.locator("#extraction-test-run-btn").click();
    // dropzone clears immediately
    await expect(page.locator("#extraction-test-dropzone-idle")).not.toHaveClass(/hidden/);
    // status ticker visible while polling
    await expect(page.locator("#extraction-test-status")).toBeVisible();
    await page.waitForTimeout(600);
  });

  // === 6. Result renders ====================================================
  await test.step("Result renders", async () => {
    await expect(page.locator("#extraction-test-results")).not.toHaveClass(/hidden/, {
      timeout: 15000,
    });
    await expect(page.locator(".extraction-result-filename")).toHaveText("us-passport.jpg");
    await expect(page.locator(".extraction-result-time")).toContainText("13.9s");
    await expect(page.locator("#extraction-test-result-fields")).toContainText("Given Name");
    await page.waitForTimeout(1500);

    // scroll the fields table so all fields are visible in the recording
    await page.locator("#extraction-test-result-fields").evaluate((el) => {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    await page.waitForTimeout(1200);
  });
});
