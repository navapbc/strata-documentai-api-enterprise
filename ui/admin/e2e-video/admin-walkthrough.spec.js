import { test, expect } from "@playwright/test";
import { JOB_ID, COMPLETED_DOC, previewDataUrl } from "../../shared/e2e/fixtures/recording/w2-document.js";
import { JOB_ID as PASSPORT_JOB_ID, COMPLETED_DOC as PASSPORT_DOC, previewDataUrl as passportPreviewDataUrl } from "../../shared/e2e/fixtures/recording/passport-document.js";
import { hoverFields, expectBboxOverlay, SELECTORS } from "../../shared/e2e/helpers/document-viewer.js";
import { TENANTS, KEYS, USERS, DOCUMENTS, AUDIT_EVENTS, DOC_CATEGORIES, EXTRACTION_FIELDS, METRICS_RESP, USAGE_RESP, SCHEMAS } from "../../shared/e2e/fixtures/recording/admin-data.js";
import { registerConfig, registerTenants, loginAs } from "../../shared/e2e/helpers/routes.js";

// ---------------------------------------------------------------------------
// Scripted, re-generatable DEMO VIDEO of the DocumentAI Admin Console.
//
// Drives the real SPA through the full flow:
//   login -> MFA -> Console Access (Users, Audit Log)
//         -> API Management (Tenants, API Keys, Manage Blueprints, Doc Categories, Extraction Rules)
//         -> Documents (Recently Processed, Search)
//         -> QA Tools (Extraction Test Runner)
//         -> Reporting (Metrics, Usage)
//
// All network dependencies are mocked - runs offline, no credentials needed.
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
  registerConfig(page);

  await page.route("**/v1/admin/extraction-test", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill(json({ jobId: PASSPORT_JOB_ID }));
    }
    route.continue();
  });
  await page.route(`**/v1/admin/extraction-test/${PASSPORT_JOB_ID}**`, (route) =>
    route.fulfill(json({ jobId: PASSPORT_JOB_ID, isCompleted: true, isFailed: false })),
  );

  // --- API: all admin endpoints --------------------------------------------
  await page.route("**/v1/admin/api-keys**", (route) =>
    route.fulfill(json({ keys: KEYS })),
  );
  registerTenants(page, TENANTS, { "acme-corp": { ...TENANTS[0], enabledDocumentTypes: null } });
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
    if (url.includes(`/documents/${PASSPORT_JOB_ID}/preview`)) {
      return route.fulfill(json({ url: passportPreviewDataUrl() }));
    }
    if (url.includes(`/documents/${PASSPORT_JOB_ID}`)) {
      return route.fulfill(json(PASSPORT_DOC));
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
    if (route.request().url().includes("/dictionary/schemas")) {
      return route.fulfill(json({ schemas: SCHEMAS }));
    }
    return route.fulfill(json({ fields: [] }));
  });
  await page.route("**/v1/config/extraction-rules**", (route) => route.fulfill(json({ rules: [{ requiredFields: ["wages", "federalIncomeTaxWithheld"], optionalFields: ["employerName", "employeeName", "taxYear"] }] })));

  // === 1. Start logged in ==================================================
  await test.step("Start logged in", async () => {
    await loginAs(page);
    await expect(page.locator("#view-title")).toHaveText("Home");
  });

  // === 2. Console Access: Users ==========================================
  await test.step("Console Access: Users", async () => {
    await expect(page.locator("#view-title")).toHaveText("Home");
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

  // === 6. API Management: Manage Blueprints ================================
  await test.step("API Management: Manage Blueprints", async () => {
    await page.locator('a.nav-item[data-view="blueprints"]').click();
    await expect(page.locator("#view-title")).toHaveText(/^Manage Blueprints/);
    await expect(page.locator("#blueprints-table")).toBeVisible();
    await page.waitForTimeout(800);

    // Select a tenant to show the Enabled toggles
    await page.locator("#tenant-select").selectOption("acme-corp");
    await expect(page.locator("#blueprints-table")).toBeVisible();
    await page.waitForTimeout(1200);

    // Search filter
    await page.locator("#blueprints-search").fill("identity");
    await page.waitForTimeout(600);
    await page.locator("#blueprints-search").fill("");
    await page.waitForTimeout(600);
  });

  // === 7. API Management: Document Categories ==============================
  await test.step("API Management: Document Categories", async () => {
    await page.locator('a.nav-item[data-view="doc-categories"]').click();
    await expect(page.locator("#view-title")).toHaveText(/^Manage Document Categories/);
    await expect(page.locator("#categories-table")).toBeVisible();
    await page.waitForTimeout(1200);
  });

  // === 8. API Management: Extraction Rules =================================
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

  // === 9. Documents: Recently Processed ====================================
  await test.step("Documents: Recently Processed", async () => {
    await page.locator('[data-section="docs"]').click();
    await expect(page.locator("#section-docs")).not.toHaveClass(/hidden/);
    await page.locator('a.nav-item[data-view="documents"]').click();
    await expect(page.locator("#view-title")).toHaveText(/^Recently Processed/);
    await expect(page.locator("#document-status-filter")).toBeVisible();
    await page.locator(SELECTORS.tenantSelect).selectOption("acme-corp");
    await expect(page.locator("#documents-list .doc-list-item").first()).toBeVisible();
    await page.waitForTimeout(800);

    await page.locator(`[data-job-id="${JOB_ID}"]`).click();
    await expect(page.locator(SELECTORS.detailPane)).toBeVisible();
    await expectBboxOverlay(page, expect, SELECTORS.bboxOverlay);
    await page.waitForTimeout(800);

    await hoverFields(page, ["wages", "federalIncomeTaxWithheld"], SELECTORS.fieldRows);
    await page.waitForTimeout(600);
  });

  // === 10. QA Tools: Extraction Test Runner =================================
  await test.step("QA Tools: Extraction Test Runner", async () => {
    await page.locator('[data-section="qa-tools"]').click();
    await expect(page.locator("#section-qa-tools")).not.toHaveClass(/hidden/);
    await page.locator('a.nav-item[data-view="extraction-test-runner"]').click();
    await expect(page.locator("#view-title")).toHaveText("Extraction Test Runner");
    await expect(page.locator("#extraction-test-empty")).toBeVisible();
    await page.waitForTimeout(600);

    await page.locator("#tenant-select").selectOption("acme-corp");
    await page.waitForTimeout(600);

    await page.locator("#extraction-test-file").setInputFiles({
      name: "us-passport.jpg",
      mimeType: "image/jpeg",
      buffer: Buffer.from("x"),
    });
    await expect(page.locator("#extraction-test-run-btn")).toBeEnabled();
    await page.waitForTimeout(600);

    await page.locator("#extraction-test-run-btn").click();
    await expect(page.locator("#extraction-test-results")).not.toHaveClass(/hidden/, {
      timeout: 15000,
    });
    await expect(page.locator(".extraction-result-filename")).toHaveText("us-passport.jpg");
    await page.waitForTimeout(1500);
  });

  // === 12. Reporting: Metrics ==============================================
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

  // === 13. Reporting: Usage ================================================
  await test.step("Reporting: Usage Tracking", async () => {
    await page.locator('a.nav-item[data-view="usage"]').click();
    await expect(page.locator("#view-title")).toHaveText(/^Usage Tracking/);
    await expect(page.locator(".usage-table")).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(1200);
  });
});
