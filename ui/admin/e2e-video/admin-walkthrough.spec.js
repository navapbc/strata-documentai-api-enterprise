import { test, expect } from "@playwright/test";
import { JOB_ID, COMPLETED_DOC, previewDataUrl } from "../../shared/e2e/fixtures/recording/w2-document.js";
import { loginWithMfa } from "../../shared/e2e/helpers/login.js";
import { hoverFields, expectBboxOverlay, SELECTORS } from "../../shared/e2e/helpers/document-viewer.js";

// ---------------------------------------------------------------------------
// Scripted, re-generatable DEMO VIDEO of the DocumentAI Admin Console.
//
// Drives the real SPA through the full flow:
//   login -> MFA -> API Keys -> Tenants -> Users -> Documents
//
// Every network dependency (config.json, Cognito, all API calls) is mocked so
// this runs offline, deterministically, with no credentials or deployed infra.
// Playwright records a .webm per run (see playwright.video.config.js).
// ---------------------------------------------------------------------------

// --- Synthetic data --------------------------------------------------------

const TENANTS = [
  { tenantId: "acme-corp", displayName: "Acme Corporation", primaryContact: "ops@acme.example.com", isActive: true, createdAt: "2025-01-10T09:00:00Z" },
  { tenantId: "river-health", displayName: "River Health Systems", primaryContact: "admin@riverhealth.example.com", isActive: true, createdAt: "2025-03-22T14:30:00Z" },
  { tenantId: "metro-transit", displayName: "Metro Transit Authority", primaryContact: "it@metrotransit.example.com", isActive: true, createdAt: "2025-05-05T11:15:00Z" },
];

const KEYS = [
  { tenantId: "acme-corp", apiKeyName: "acme-ingest", emailAddress: "ops@acme.example.com", environment: "prod", keyPrefix: "sk_prod_acme", createdAt: "2025-02-01T08:00:00Z", lastUsed: "2026-07-15T22:10:00Z" },
  { tenantId: "acme-corp", apiKeyName: "acme-staging", emailAddress: "dev@acme.example.com", environment: "staging", keyPrefix: "sk_stg_acme", createdAt: "2025-02-01T08:05:00Z", lastUsed: "2026-07-14T10:00:00Z" },
  { tenantId: "river-health", apiKeyName: "rh-prod", emailAddress: "admin@riverhealth.example.com", environment: "prod", keyPrefix: "sk_prod_rh", createdAt: "2025-04-01T12:00:00Z", lastUsed: "2026-07-16T08:45:00Z" },
  { tenantId: "metro-transit", apiKeyName: "mt-ingest", emailAddress: "it@metrotransit.example.com", environment: "prod", keyPrefix: "sk_prod_mt", createdAt: "2025-06-01T09:30:00Z", lastUsed: null },
];

const USERS = [
  { username: "user-001", email: "admin@acme.example.com", status: "approved", role: "tenant-admin", tenantId: "acme-corp", createdAt: "2025-02-01T07:00:00Z" },
  { username: "user-002", email: "ops@riverhealth.example.com", status: "approved", role: "tenant-admin", tenantId: "river-health", createdAt: "2025-03-22T14:00:00Z" },
  { username: "user-003", email: "newuser@metrotransit.example.com", status: "pending", role: null, tenantId: null, createdAt: "2026-07-16T09:00:00Z" },
];

const DOCUMENTS = [
  { jobId: JOB_ID, fileName: "employee-w2-2025.png", processStatus: "success", matchedBlueprint: "US Tax Form W-2", tenantId: "acme-corp", createdAt: "2026-07-16T15:55:00Z" },
  { jobId: "job-002", fileName: "invoice-4471.pdf", processStatus: "success", matchedBlueprint: "Invoice", tenantId: "acme-corp", createdAt: "2026-07-16T15:10:00Z" },
  { jobId: "job-003", fileName: "drivers-license.jpg", processStatus: "success", matchedBlueprint: "US Driver License", tenantId: "river-health", createdAt: "2026-07-16T14:30:00Z" },
  { jobId: "job-004", fileName: "blurry-scan.png", processStatus: "blurry_document_detected", matchedBlueprint: null, tenantId: "acme-corp", createdAt: "2026-07-15T22:05:00Z" },
  { jobId: "job-005", fileName: "receipt-scan.png", processStatus: "no_custom_blueprint_matched", matchedBlueprint: null, tenantId: "metro-transit", createdAt: "2026-07-15T18:30:00Z" },
];

// ---------------------------------------------------------------------------

test("admin console walkthrough: login -> MFA -> keys -> tenants -> users -> documents", async ({
  page,
}) => {
  const json = (body) => ({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(body),
  });

  // --- config.json: no Google SSO, dummy Cognito ids -----------------------
  await page.route("**/config.json", (route) =>
    route.fulfill(
      json({
        api_endpoint: { value: "https://api.admin.local" },
        cognito_user_pool_id: { value: "us-east-1_ADMIN0000" },
        cognito_client_id: { value: "adminclientid000000000000" },
        cognito_domain: { value: null },
        cognito_google_enabled: { value: false },
      }),
    ),
  );

  // --- API: all admin endpoints --------------------------------------------
  await page.route("**/v1/admin/api-keys**", (route) =>
    route.fulfill(json({ keys: KEYS })),
  );
  await page.route("**/v1/admin/tenants**", (route) =>
    route.fulfill(json({ tenants: TENANTS })),
  );
  await page.route("**/v1/admin/users**", (route) =>
    route.fulfill(json({ users: USERS })),
  );
  await page.route("**/v1/admin/documents**", (route) => {
    const url = route.request().url();
    if (url.includes(`/documents/${JOB_ID}/preview`)) {
      return route.fulfill(json({ url: previewDataUrl() }));
    }
    if (url.includes(`/documents/${JOB_ID}`)) {
      return route.fulfill(json(COMPLETED_DOC));
    }
    const status = new URL(url).searchParams.get("status_filter");
    const docs = status ? DOCUMENTS.filter((d) => d.processStatus === status) : DOCUMENTS;
    return route.fulfill(json({ documents: docs, cursor: null }));
  });
  await page.route("**/v1/audit/**", (route) => route.fulfill(json({})));
  await page.route("**/v1/dictionary/**", (route) =>
    route.fulfill(json({ fields: [] })),
  );

  // === 1. Login + MFA ======================================================
  await page.goto("/");
  await loginWithMfa(page, { expect });

  // === 2. Dashboard: Tenants ===============================================
  await expect(page.locator("#view-title")).toHaveText("");
  await page.locator('[data-section="tenants"]').click();
  await expect(page.locator("#section-tenants")).not.toHaveClass(/hidden/);
  await page.locator('a.nav-item[data-view="tenants"]').click();
  await expect(page.locator("#view-title")).toHaveText(/^Manage Tenants/);
  await expect(page.locator("#tenants-table")).toBeVisible();
  await page.waitForTimeout(1200);

  // === 4. Navigate to Users ================================================
  await page.locator('[data-section="users"]').click();
  await expect(page.locator("#section-users")).not.toHaveClass(/hidden/);
  await page.locator('a.nav-item[data-view="users"]').click();
  await expect(page.locator("#view-title")).toHaveText(/^Manage Users/);
  await expect(page.locator("#users-table")).toBeVisible();
  await page.waitForTimeout(1200);

  // === 5. Navigate to API Keys =============================================
  await page.locator('[data-section="keys"]').click();
  await expect(page.locator("#section-keys")).not.toHaveClass(/hidden/);
  await page.locator('a.nav-item[data-view="keys"]').click();
  await expect(page.locator("#view-title")).toHaveText(/^Manage API Keys/);
  await expect(page.locator("#keys-table")).toBeVisible();
  await page.waitForTimeout(1200);

  // === 6. Navigate to Documents ============================================
  await page.locator('[data-section="docs"]').click();
  await expect(page.locator("#section-docs")).not.toHaveClass(/hidden/);
  await page.locator('a.nav-item[data-view="documents"]').click();
  await expect(page.locator("#view-title")).toHaveText(/^Recently Processed/);
  await expect(page.locator("#document-status-filter")).toBeVisible();
  await page.waitForTimeout(600);

  // Select a tenant so the document list loads
  await page.locator(SELECTORS.tenantSelect).selectOption("acme-corp");
  await expect(page.locator("#documents-list .doc-list-item").first()).toBeVisible();
  await page.waitForTimeout(900);

  // Scroll the list to show all documents
  await page.locator("#documents-list").evaluate((el) => el.scrollTo({ top: el.scrollHeight, behavior: "smooth" }));
  await page.waitForTimeout(800);
  await page.locator("#documents-list").evaluate((el) => el.scrollTo({ top: 0, behavior: "smooth" }));
  await page.waitForTimeout(600);

  // Click the W-2 to show detail panel + bounding box overlay
  await page.locator(`[data-job-id="${JOB_ID}"]`).click();
  await expect(page.locator(SELECTORS.detailPane)).toBeVisible();
  await expectBboxOverlay(page, expect, SELECTORS.bboxOverlay);
  await page.waitForTimeout(1000);

  // Hover field rows to show bbox highlight
  await hoverFields(page, ["wages", "federalIncomeTaxWithheld", "employerName"], SELECTORS.fieldRows);

  // Show the status filter dropdown
  await page.locator("#document-status-filter").click();
  await page.waitForTimeout(700);
  await page.locator("#document-status-filter").selectOption("success");
  await page.waitForTimeout(1000);

  // Reset to all statuses
  await page.locator("#document-status-filter").selectOption("");
  await page.waitForTimeout(1200);
});
