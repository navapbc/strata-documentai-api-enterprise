import { test, expect } from "@playwright/test";

// ---------------------------------------------------------------------------
// Scripted demo video: Extraction Rules management view.
//
// Flow: login -> MFA -> Documents -> Extraction Rules
//       -> select tenant -> browse blueprints -> toggle fields -> save
// ---------------------------------------------------------------------------

const TENANT_ID = "acme-corp";

const FIELDS = [
  // W-2
  { name: "employerName",            documentType: "US Tax Form W-2", type: "string" },
  { name: "employeeName",            documentType: "US Tax Form W-2", type: "string" },
  { name: "socialSecurityNumber",    documentType: "US Tax Form W-2", type: "string" },
  { name: "wages",                   documentType: "US Tax Form W-2", type: "currency" },
  { name: "federalIncomeTaxWithheld",documentType: "US Tax Form W-2", type: "currency" },
  { name: "taxYear",                 documentType: "US Tax Form W-2", type: "integer" },
  // Invoice
  { name: "invoiceNumber",  documentType: "Invoice", type: "string" },
  { name: "invoiceDate",    documentType: "Invoice", type: "date" },
  { name: "vendorName",     documentType: "Invoice", type: "string" },
  { name: "totalAmount",    documentType: "Invoice", type: "currency" },
  { name: "lineItems",      documentType: "Invoice", type: "array" },
  // Driver License
  { name: "fullName",       documentType: "US Driver License", type: "string" },
  { name: "dateOfBirth",    documentType: "US Driver License", type: "date" },
  { name: "licenseNumber",  documentType: "US Driver License", type: "string" },
  { name: "expirationDate", documentType: "US Driver License", type: "date" },
  { name: "address",        documentType: "US Driver License", type: "string" },
];

// Initial rules for W-2: wages + federalIncomeTaxWithheld required, rest optional
const W2_RULES = {
  rules: [{
    requiredFields: ["wages", "federalIncomeTaxWithheld"],
    optionalFields: ["employerName", "employeeName", "socialSecurityNumber", "taxYear"],
  }],
};

// No rules yet for Invoice
const EMPTY_RULES = { rules: [] };

test("extraction rules walkthrough", async ({ page }) => {
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

  // --- Cognito --------------------------------------------------------------
  await page.route(/cognito-idp\./, async (route) => {
    const target = route.request().headers()["x-amz-target"] || "";
    if (target.includes("InitiateAuth")) {
      return route.fulfill(json({ ChallengeName: "SOFTWARE_TOKEN_MFA", Session: "session" }));
    }
    if (target.includes("RespondToAuthChallenge")) {
      const payload = btoa(JSON.stringify({ "cognito:groups": ["super-admin"], email: "admin@example.com" }));
      return route.fulfill(json({
        AuthenticationResult: {
          AccessToken: "admin-access-token",
          IdToken: `h.${payload}.s`,
          RefreshToken: "admin-refresh-token",
          ExpiresIn: 3600,
        },
      }));
    }
    return route.fulfill(json({}));
  });

  // --- API ------------------------------------------------------------------
  await page.route("**/v1/admin/tenants**", (route) =>
    route.fulfill(json({ tenants: [{ tenantId: TENANT_ID, displayName: "Acme Corporation", isActive: true }] })),
  );
  await page.route("**/v1/dictionary/**", (route) => route.fulfill(json({ fields: [] })));
  await page.route("**/v1/dictionary/fields*", (route) =>
    route.fulfill(json({ fields: FIELDS })),
  );
  await page.route("**/v1/config/extraction-rules**", (route) => {
    const url = route.request().url();
    const method = route.request().method();
    if (method === "PUT") return route.fulfill(json({ ok: true }));
    const docType = new URL(url).searchParams.get("document_type") || "";
    if (docType === "US Tax Form W-2") return route.fulfill(json(W2_RULES));
    return route.fulfill(json(EMPTY_RULES));
  });
  await page.route("**/v1/audit/**", (route) => route.fulfill(json({})));

  // === 1. Login =============================================================
  await page.goto("/");
  await expect(page.locator("#sign-in-card")).toBeVisible();
  await page.fill("#sign-in-email", "admin@example.com");
  await page.fill("#sign-in-password", "AdminPassword123!");
  await page.waitForTimeout(600);
  await page.click('#sign-in-form button[type="submit"]');

  // === 2. MFA ===============================================================
  await expect(page.locator("#mfa-card")).toBeVisible();
  await page.fill("#mfa-code", "123456");
  await page.waitForTimeout(500);
  await page.click('#mfa-form button[type="submit"]');

  // === 3. Navigate to Extraction Rules =====================================
  await page.locator('[data-section="docs"]').click();
  await expect(page.locator("#section-docs")).not.toHaveClass(/hidden/);
  await page.locator('[data-view="extraction-rules"]').click();
  await expect(page.locator("#view-title")).toHaveText("Manage Extraction Rules");
  await page.waitForTimeout(800);

  // === 4. Select tenant =====================================================
  await page.locator("#global-tenant-select").selectOption(TENANT_ID);
  await page.waitForTimeout(600);

  // === 5. Blueprint list should be populated ================================
  await expect(page.locator("#bp-list-pane .nav-item").first()).toBeVisible({ timeout: 15000 });

  // === 6. Click W-2 blueprint ===============================================
  await page.locator('#bp-list-pane .nav-item', { hasText: "US Tax Form W-2" }).click();
  await expect(page.locator("#bp-fields-list h3")).toHaveText("US Tax Form W-2");
  await expect(page.locator(".field-row").first()).toBeVisible();
  await page.waitForTimeout(1000);

  // === 7. Scroll field list to show all fields ==============================
  await page.locator("#bp-fields-list").evaluate((el) => el.scrollTo({ top: el.scrollHeight, behavior: "smooth" }));
  await page.waitForTimeout(700);
  await page.locator("#bp-fields-list").evaluate((el) => el.scrollTo({ top: 0, behavior: "smooth" }));
  await page.waitForTimeout(600);

  // === 8. Toggle socialSecurityNumber to required ===========================
  await page.locator('.field-row').filter({ hasText: 'socialSecurityNumber' }).locator('.toggle-label:has(input[value="required"])').click();
  await page.waitForTimeout(700);

  // === 9. Toggle taxYear to excluded ========================================
  await page.locator('.field-row').filter({ hasText: 'taxYear' }).locator('.toggle-label:has(input[value="excluded"])').click();
  await page.waitForTimeout(700);

  // === 10. Save =============================================================
  await page.locator("#bp-save-btn").click();
  await page.waitForTimeout(800);

  // === 11. Switch to Invoice blueprint ======================================
  await page.locator('#bp-list-pane .nav-item', { hasText: "Invoice" }).click();
  await expect(page.locator("#bp-fields-list h3")).toHaveText("Invoice");
  await page.waitForTimeout(1000);

  // === 12. Toggle a couple of Invoice fields ================================
  await page.locator('.field-row').filter({ hasText: 'invoiceNumber' }).locator('.toggle-label:has(input[value="required"])').click();
  await page.waitForTimeout(600);
  await page.locator('.field-row').filter({ hasText: 'totalAmount' }).locator('.toggle-label:has(input[value="required"])').click();
  await page.waitForTimeout(600);
  await page.locator('.field-row').filter({ hasText: 'lineItems' }).locator('.toggle-label:has(input[value="excluded"])').click();
  await page.waitForTimeout(800);

  // === 13. Save Invoice rules ===============================================
  await page.locator("#bp-save-btn").click();
  await page.waitForTimeout(1200);
});
