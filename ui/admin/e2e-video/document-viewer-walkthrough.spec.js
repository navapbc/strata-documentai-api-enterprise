import { test, expect } from "@playwright/test";
import { JOB_ID, COMPLETED_DOC, FIELDS, previewDataUrl } from "../../shared/e2e/fixtures/recording/w2-document.js";
import { loginWithMfa } from "../../shared/e2e/helpers/login.js";
import { hoverFields, expectBboxOverlay } from "../../shared/e2e/helpers/document-viewer.js";

// ---------------------------------------------------------------------------
// Scripted demo video: Document viewer with bounding box overlay.
//
// Flow: login -> MFA -> Documents -> open W-2 -> bbox overlay -> field hover
//
// All network dependencies are mocked — runs offline, no credentials needed.
// ---------------------------------------------------------------------------

const TENANT_ID = "acme-corp";

const DOCUMENTS = [
  { jobId: JOB_ID, fileName: "employee-w2-2025.png", processStatus: "success", matchedBlueprint: "US Tax Form W-2", tenantId: TENANT_ID, createdAt: "2026-07-16T15:55:00Z" },
  { jobId: "job-002", fileName: "invoice-4471.pdf", processStatus: "success", matchedBlueprint: "Invoice", tenantId: TENANT_ID, createdAt: "2026-07-16T15:10:00Z" },
  { jobId: "job-003", fileName: "drivers-license.jpg", processStatus: "success", matchedBlueprint: "US Driver License", tenantId: TENANT_ID, createdAt: "2026-07-16T14:30:00Z" },
];

test("document viewer walkthrough: bbox overlay and field highlighting", async ({ page }) => {
  const json = (body) => ({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(body),
  });

  // --- config.json ----------------------------------------------------------
  await page.route("**/config.json", (route) =>
    route.fulfill(json({
      api_endpoint: { value: "https://api.admin.local" },
      cognito_user_pool_id: { value: "us-east-1_ADMIN0000" },
      cognito_client_id: { value: "adminclientid000000000000" },
      cognito_domain: { value: null },
      cognito_google_enabled: { value: false },
    })),
  );

  // --- API ------------------------------------------------------------------
  await page.route("**/v1/admin/tenants**", (route) =>
    route.fulfill(json({ tenants: [{ tenantId: TENANT_ID, displayName: "Acme Corporation", isActive: true }] })),
  );
  await page.route("**/v1/admin/documents**", (route) => {
    const url = route.request().url();
    if (url.includes(`/documents/${JOB_ID}/preview`)) {
      return route.fulfill(json({ url: previewDataUrl() }));
    }
    if (url.includes(`/documents/${JOB_ID}`)) {
      return route.fulfill(json(COMPLETED_DOC));
    }
    return route.fulfill(json({ documents: DOCUMENTS, cursor: null }));
  });
  await page.route("**/v1/audit/**", (route) => route.fulfill(json({})));
  await page.route("**/v1/dictionary/**", (route) => route.fulfill(json({ fields: [] })));

  // === 1. Login + MFA =======================================================
  await page.goto("/");
  await loginWithMfa(page, { expect });

  // === 2. Navigate to Documents ============================================
  await page.locator('[data-section="docs"]').click();
  await expect(page.locator("#section-docs")).not.toHaveClass(/hidden/);
  await page.locator('[data-view="documents"]').click();
  await expect(page.locator("#view-title")).toHaveText("Recently Processed");
  await page.waitForTimeout(600);

  // === 3. Select tenant =====================================================
  await page.locator("#global-tenant-select").selectOption(TENANT_ID);
  await expect(page.locator("#documents-list .doc-list-item").first()).toBeVisible();
  await page.waitForTimeout(900);

  // === 4. Open the W-2 document ============================================
  await page.locator(`[data-job-id="${JOB_ID}"]`).click();
  await expect(page.locator("#document-detail-panel")).not.toHaveClass(/collapsed/);
  await page.waitForTimeout(800);

  // === 5. Bbox overlay =====================================================
  await expectBboxOverlay(page, expect, "#document-preview-panel .bbox-overlay rect");
  await page.waitForTimeout(1000);

  // === 6. Hover each field to show highlight linking =======================
  await hoverFields(
    page,
    FIELDS.map((f) => f.name),
    "#document-detail-panel tr[data-field]",
    900,
  );

  await page.waitForTimeout(1200);
});
