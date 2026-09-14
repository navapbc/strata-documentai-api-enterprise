import { test, expect } from "@playwright/test";
import { JOB_ID, COMPLETED_DOC, previewDataUrl } from "../../shared/e2e/fixtures/recording/w2-document.js";
import { loginWithMfa } from "../../shared/e2e/helpers/login.js";
import { hoverFields, expectBboxOverlay, SELECTORS } from "../../shared/e2e/helpers/document-viewer.js";

// ---------------------------------------------------------------------------
// Scripted, re-generatable DEMO VIDEO of the DocumentAI Admin Console.
//
// Drives the real SPA through the full flow:
//   login -> MFA -> Console Access (Users, Audit Log)
//         -> API Management (Tenants, API Keys, Doc Categories, Extraction Rules)
//         -> Documents (Recently Processed, Search)
//         -> Reporting (Metrics, Usage)
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

const AUDIT_EVENTS = [
  { eventId: "evt-001", timestamp: "2026-07-16T15:00:00Z", actorEmail: "admin@example.com", action: "tenant.create", targetType: "tenant", targetId: "metro-transit", tenantId: null, metadata: {} },
  { eventId: "evt-002", timestamp: "2026-07-16T14:30:00Z", actorEmail: "admin@example.com", action: "api-key.create", targetType: "api-key", targetId: "mt-ingest", tenantId: "metro-transit", metadata: {} },
  { eventId: "evt-003", timestamp: "2026-07-16T09:10:00Z", actorEmail: "admin@example.com", action: "user.approve", targetType: "user", targetId: "user-003", tenantId: null, metadata: {} },
  { eventId: "evt-004", timestamp: "2026-07-15T22:00:00Z", actorEmail: "admin@example.com", action: "extraction-rules.update", targetType: "extraction-rules", targetId: "acme-corp", tenantId: "acme-corp", metadata: { documentType: "US Tax Form W-2" } },
  { eventId: "evt-005", timestamp: "2026-07-15T18:00:00Z", actorEmail: "admin@example.com", action: "doc-category.create", targetType: "doc-category", targetId: "pay-stub", tenantId: "acme-corp", metadata: {} },
];

const DOC_CATEGORIES = [
  { tenantId: "acme-corp", categoryName: "pay-stub", displayName: "Pay Stub", description: "Employee pay stubs", processingPercentage: 1, isAutoRegistered: false, isActive: true, createdAt: "2026-07-15T18:00:00Z" },
  { tenantId: "acme-corp", categoryName: "w2-form", displayName: "W-2 Form", description: "Annual tax forms", processingPercentage: 1, isAutoRegistered: true, isActive: true, createdAt: "2026-01-10T09:00:00Z" },
  { tenantId: "river-health", categoryName: "drivers-license", displayName: "Driver License", description: "State-issued ID", processingPercentage: 0.5, isAutoRegistered: false, isActive: true, createdAt: "2026-03-22T14:00:00Z" },
];

const EXTRACTION_FIELDS = [
  { name: "employerName", documentType: "US Tax Form W-2", type: "string" },
  { name: "employeeName", documentType: "US Tax Form W-2", type: "string" },
  { name: "wages", documentType: "US Tax Form W-2", type: "currency" },
  { name: "federalIncomeTaxWithheld", documentType: "US Tax Form W-2", type: "currency" },
  { name: "taxYear", documentType: "US Tax Form W-2", type: "integer" },
  { name: "invoiceNumber", documentType: "Invoice", type: "string" },
  { name: "invoiceDate", documentType: "Invoice", type: "date" },
  { name: "totalAmount", documentType: "Invoice", type: "currency" },
];

const METRICS_RESP = {
  summary: {
    totalRecords: 1840,
    totalExtractionInvocations: 1720,
    totalDocumentsRecognized: 1650,
    byResponseCode: { "000": 1580, "101": 70, "410": 60, "900": 130 },
    byClassification: { "US Tax Form W-2": 820, "Invoice": 540, "US Driver License": 290, "null": 190 },
    byFileType: { "image/png": 910, "image/jpeg": 540, "application/pdf": 390 },
    byUserCategory: { "pay-stub": 480, "w2-form": 820, "drivers-license": 290, "null": 250 },
    byUploadMethod: { "api": 1640, "console": 200 },
    timingStats: { bdaProcessingTimeAvg: 27.1, bdaWaitTimeAvg: 2.3, totalProcessingTimeAvg: 29.4 },
  },
  dailyStats: [
    { date: "2026-07-10", totalRecords: 240, bdaInvocations: 225, successCount: 210, bdaProcessingTimeAvg: 26.8, totalProcessingTimeAvg: 29.1 },
    { date: "2026-07-11", totalRecords: 195, bdaInvocations: 182, successCount: 174, bdaProcessingTimeAvg: 27.3, totalProcessingTimeAvg: 29.6 },
    { date: "2026-07-12", totalRecords: 310, bdaInvocations: 291, successCount: 278, bdaProcessingTimeAvg: 27.0, totalProcessingTimeAvg: 29.3 },
    { date: "2026-07-13", totalRecords: 280, bdaInvocations: 263, successCount: 251, bdaProcessingTimeAvg: 27.4, totalProcessingTimeAvg: 29.7 },
    { date: "2026-07-14", totalRecords: 320, bdaInvocations: 300, successCount: 287, bdaProcessingTimeAvg: 26.9, totalProcessingTimeAvg: 29.2 },
    { date: "2026-07-15", totalRecords: 265, bdaInvocations: 248, successCount: 237, bdaProcessingTimeAvg: 27.2, totalProcessingTimeAvg: 29.5 },
    { date: "2026-07-16", totalRecords: 230, bdaInvocations: 211, successCount: 143, bdaProcessingTimeAvg: 27.5, totalProcessingTimeAvg: 29.8 },
  ],
};

const USAGE_RESP = {
  tenants: [
    { tenantId: "acme-corp", totalRecords: 980, totalBdaPages: 1240, totalFileSizeBytes: 312_000_000 },
    { tenantId: "river-health", totalRecords: 540, totalBdaPages: 680, totalFileSizeBytes: 178_000_000 },
    { tenantId: "metro-transit", totalRecords: 320, totalBdaPages: 410, totalFileSizeBytes: 104_000_000 },
  ],
};

// ---------------------------------------------------------------------------

test("admin console walkthrough", async ({
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
  await page.route("**/v1/admin/audit-log/actions**", (route) => route.fulfill(json({ actions: ["tenant.create", "api-key.create", "user.approve", "extraction-rules.update", "doc-category.create"] })));
  await page.route("**/v1/admin/audit-log/actors**", (route) => route.fulfill(json({ actors: ["admin@example.com"] })));
  await page.route("**/v1/admin/audit-log**", (route) => route.fulfill(json({ events: AUDIT_EVENTS, nextCursor: null })));
  await page.route("**/v1/metrics**", (route) => route.fulfill(json(METRICS_RESP)));
  await page.route("**/v1/admin/usage**", (route) => route.fulfill(json(USAGE_RESP)));
  await page.route("**/v1/admin/document-categories**", (route) => route.fulfill(json({ categories: DOC_CATEGORIES })));
  await page.route("**/v1/dictionary/**", (route) => {
    if (route.request().url().includes("/dictionary/fields")) {
      return route.fulfill(json({ fields: EXTRACTION_FIELDS }));
    }
    return route.fulfill(json({ fields: [] }));
  });
  await page.route("**/v1/config/extraction-rules**", (route) => route.fulfill(json({ rules: [{ requiredFields: ["wages", "federalIncomeTaxWithheld"], optionalFields: ["employerName", "employeeName", "taxYear"] }] })));

  // === 1. Login + MFA ======================================================
  await test.step("Login + MFA", async () => {
    await page.addInitScript(() => sessionStorage.clear());
    await page.goto("/");
    await loginWithMfa(page, { expect });
  });

  // === 2. Console Access: Users ==========================================
  await test.step("Console Access: Users", async () => {
    await expect(page.locator("#view-title")).toHaveText("");
    await page.locator('[data-section="console-access"]').click();
    await expect(page.locator("#section-console-access")).not.toHaveClass(/hidden/);
    await page.locator('a.nav-item[data-view="users"]').click();
    await expect(page.locator("#view-title")).toHaveText(/^Manage Users/);
    await expect(page.locator("#users-table")).toBeVisible();
    await page.waitForTimeout(1200);
  });

  // === 3. Console Access: Audit Log ========================================
  await test.step("Console Access: Audit Log", async () => {
    await page.locator('a.nav-item[data-view="audit-log"]').click();
    await expect(page.locator("#view-title")).toHaveText(/^Audit Log/);
    await expect(page.locator("#audit-table")).toBeVisible();
    await page.waitForTimeout(1200);
  });

  // === 4. API Management: Tenants ==========================================
  await test.step("API Management: Tenants", async () => {
    await page.locator('[data-section="management"]').click();
    await expect(page.locator("#section-management")).not.toHaveClass(/hidden/);
    await page.locator('a.nav-item[data-view="tenants"]').click();
    await expect(page.locator("#view-title")).toHaveText(/^Manage Tenants/);
    await expect(page.locator("#tenants-table")).toBeVisible();
    await page.waitForTimeout(1200);
  });

  // === 5. API Management: API Keys =========================================
  await test.step("API Management: API Keys", async () => {
    await page.locator('a.nav-item[data-view="keys"]').click();
    await expect(page.locator("#view-title")).toHaveText(/^Manage API Keys/);
    await expect(page.locator("#keys-table")).toBeVisible();
    await page.waitForTimeout(1200);
  });

  // === 6. API Management: Document Categories ==============================
  await test.step("API Management: Document Categories", async () => {
    await page.locator('a.nav-item[data-view="doc-categories"]').click();
    await expect(page.locator("#view-title")).toHaveText(/^Manage Document Categories/);
    await expect(page.locator("#categories-table")).toBeVisible();
    await page.waitForTimeout(1200);
  });

  // === 7. API Management: Extraction Rules =================================
  await test.step("API Management: Extraction Rules", async () => {
    await page.locator('a.nav-item[data-view="extraction-rules"]').click();
    await expect(page.locator("#view-title")).toHaveText(/^Manage Extraction Rules/);
    await page.locator("#tenant-select").selectOption("acme-corp");
    await page.waitForTimeout(600);
    await page.locator("#bp-list-pane .combobox-input").click();
    await expect(page.locator("#bp-list-pane .combobox-option").first()).toBeVisible({ timeout: 10000 });
    await page.locator("#bp-list-pane .combobox-option", { hasText: "US Tax Form W-2" }).click();
    await expect(page.locator("#bp-fields-list h3")).toHaveText("US Tax Form W-2");
    await page.waitForTimeout(1200);
  });

  // === 8. Documents: Recently Processed ====================================
  await test.step("Documents: Recently Processed", async () => {
    await page.locator('[data-section="docs"]').click();
    await expect(page.locator("#section-docs")).not.toHaveClass(/hidden/);
    await page.locator('a.nav-item[data-view="documents"]').click();
    await expect(page.locator("#view-title")).toHaveText(/^Recently Processed/);
    await expect(page.locator("#document-status-filter")).toBeVisible();
    await page.waitForTimeout(600);

    await page.locator(SELECTORS.tenantSelect).selectOption("acme-corp");
    await expect(page.locator("#documents-list .doc-list-item").first()).toBeVisible();
    await page.waitForTimeout(900);

    await page.locator("#documents-list").evaluate((el) => el.scrollTo({ top: el.scrollHeight, behavior: "smooth" }));
    await page.waitForTimeout(800);
    await page.locator("#documents-list").evaluate((el) => el.scrollTo({ top: 0, behavior: "smooth" }));
    await page.waitForTimeout(600);

    await page.locator(`[data-job-id="${JOB_ID}"]`).click();
    await expect(page.locator(SELECTORS.detailPane)).toBeVisible();
    await expectBboxOverlay(page, expect, SELECTORS.bboxOverlay);
    await page.waitForTimeout(1000);

    await hoverFields(page, ["wages", "federalIncomeTaxWithheld", "employerName"], SELECTORS.fieldRows);

    await page.locator("#document-status-filter").selectOption("success");
    await page.waitForTimeout(1000);
    await page.locator("#document-status-filter").selectOption("");
    await page.waitForTimeout(800);
  });

  // === 9. Reporting: Metrics ==============================================
  await test.step("Reporting: Metrics Dashboard", async () => {
    await page.locator('[data-section="reporting"]').click();
    await expect(page.locator("#section-reporting")).not.toHaveClass(/hidden/);
    await page.locator('a.nav-item[data-view="metrics"]').click();
    await expect(page.locator("#view-title")).toHaveText(/^Metrics Dashboard/);
    await expect(page.locator("#metrics-empty")).toHaveClass(/hidden/);
    await page.waitForTimeout(1000);
    await page.locator('.metrics-tab[data-tab="outcomes"]').click();
    await page.waitForTimeout(800);
    await page.locator('.metrics-tab[data-tab="timing"]').click();
    await page.waitForTimeout(1000);
  });

  // === 11. Reporting: Usage ================================================
  await test.step("Reporting: Usage Tracking", async () => {
    await page.locator('a.nav-item[data-view="usage"]').click();
    await expect(page.locator("#view-title")).toHaveText(/^Usage Tracking/);
    await expect(page.locator(".usage-table")).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(1200);
  });
});
