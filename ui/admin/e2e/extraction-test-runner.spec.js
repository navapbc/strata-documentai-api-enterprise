import { test, expect } from "@playwright/test";

const JOB_ID = "b1686d79-41a9-41f6-af39-28e1d3488baf";

const POLL_RESULT = {
  jobId: JOB_ID,
  isCompleted: true,
  isFailed: false,
};

const DOC_RESULT = {
  jobId: JOB_ID,
  fileName: "us-passport.jpg",
  tenantId: "e2e-test-tenant-gw0",
  processStatus: "success",
  matchedDocumentClass: "US-passports",
  createdAt: "2026-10-21T19:16:50.115856+00:00",
  totalProcessingTimeSeconds: 13.88,
  fields: {
    name: {
      given_name: { confidence: 0.98, value: "WHITNEY", displayName: "Given Name" },
      last_name: { confidence: 0.98, value: "HOUSTON", displayName: "Last Name" },
    },
    document_number: { confidence: 0.96, value: "000000003", displayName: "Document Number" },
    expiration_date: { confidence: 0.98, value: "2017-05-08", displayName: "Expiration Date" },
    date_of_birth: { confidence: 0.98, value: "1963-08-09", displayName: "Date of Birth" },
    date_of_issue: { confidence: 0.91, value: "2007-05-09", displayName: "Date of Issue" },
    place_of_birth: {
      confidence: 0.95,
      value: "NEW JERSEY U.S.A.",
      displayName: "Place of Birth",
    },
    sex: { confidence: 1.0, value: "F", displayName: "Sex" },
    passport_type: { confidence: 0.98, value: "P", displayName: "Passport Type" },
  },
};

async function setup(page) {
  // Stub POST /v1/admin/extraction-test → jobId
  await page.route("**/v1/admin/extraction-test", (route) => {
    if (route.request().method() === "POST") {
      route.fulfill({ json: { jobId: JOB_ID } });
    } else {
      route.continue();
    }
  });

  // Stub GET poll → completed immediately
  await page.route(`**/v1/admin/extraction-test/${JOB_ID}**`, (route) => {
    route.fulfill({ json: POLL_RESULT });
  });

  // Stub DocumentsService.get → enriched doc
  await page.route(`**/v1/admin/documents/${JOB_ID}**`, (route) => {
    route.fulfill({ json: DOC_RESULT });
  });

  // Stub history list → empty so it doesn't interfere
  await page.route("**/v1/admin/documents**", (route) => {
    if (!route.request().url().includes(JOB_ID)) {
      route.fulfill({ json: { documents: [] } });
    } else {
      route.continue();
    }
  });

  await page.goto("/");
  await page.evaluate(() => {
    const payload = btoa(
      JSON.stringify({ "cognito:groups": ["super-admin"], email: "admin@test.com" }),
    );
    const fakeToken = `h.${payload}.s`;
    sessionStorage.setItem(
      "docai_console_session",
      JSON.stringify({
        accessToken: "fake-at",
        idToken: fakeToken,
        refreshToken: "fake-rt",
        email: "admin@test.com",
        expiresAt: Date.now() + 3600000,
      }),
    );
  });
  await page.goto("/");
  await expect(page.locator("#view-title")).toHaveText("Manage API Keys");
}

async function navigateToRunner(page) {
  await page.locator('[data-section="qa-tools"]').click();
  await expect(page.locator("#section-qa-tools")).toBeVisible();
  await page.locator('[data-view="extraction-test-runner"]').click({ force: true });
  await expect(page.locator("#view-title")).toHaveText("Extraction Test Runner");
}

async function selectTenant(page, tenantId = "e2e-test-tenant-gw0") {
  await page.locator("#tenant-select").selectOption({ value: tenantId });
}

test.describe("Extraction Test Runner", () => {
  test("mounts the view with empty state", async ({ page }) => {
    await setup(page);
    await navigateToRunner(page);
    await expect(page.locator("#extraction-test-empty")).toBeVisible();
    await expect(page.locator("#extraction-test-results")).toHaveClass(/hidden/);
  });

  test("run button is disabled until tenant and file are both set", async ({ page }) => {
    await setup(page);
    await navigateToRunner(page);
    await expect(page.locator("#extraction-test-run-btn")).toBeDisabled();

    // Stub tenant list so selectOption works
    await page.route("**/v1/admin/tenants**", (route) =>
      route.fulfill({
        json: { tenants: [{ tenantId: "e2e-test-tenant-gw0", displayName: "E2E Tenant" }] },
      }),
    );
    await selectTenant(page);
    await expect(page.locator("#extraction-test-run-btn")).toBeDisabled();

    await page
      .locator("#extraction-test-file")
      .setInputFiles({ name: "us-passport.jpg", mimeType: "image/jpeg", buffer: Buffer.from("x") });
    await expect(page.locator("#extraction-test-run-btn")).toBeEnabled();
  });

  test("clears dropzone after run starts", async ({ page }) => {
    await setup(page);
    await navigateToRunner(page);
    await page.route("**/v1/admin/tenants**", (route) =>
      route.fulfill({
        json: { tenants: [{ tenantId: "e2e-test-tenant-gw0", displayName: "E2E Tenant" }] },
      }),
    );
    await selectTenant(page);
    await page
      .locator("#extraction-test-file")
      .setInputFiles({ name: "us-passport.jpg", mimeType: "image/jpeg", buffer: Buffer.from("x") });

    await page.locator("#extraction-test-run-btn").click();

    await expect(page.locator("#extraction-test-dropzone-idle")).not.toHaveClass(/hidden/);
    await expect(page.locator("#extraction-test-dropzone-selected")).toHaveClass(/hidden/);
  });

  test("renders result header and fields after a successful run", async ({ page }) => {
    await setup(page);
    await navigateToRunner(page);
    await page.route("**/v1/admin/tenants**", (route) =>
      route.fulfill({
        json: { tenants: [{ tenantId: "e2e-test-tenant-gw0", displayName: "E2E Tenant" }] },
      }),
    );
    await selectTenant(page);
    await page
      .locator("#extraction-test-file")
      .setInputFiles({ name: "us-passport.jpg", mimeType: "image/jpeg", buffer: Buffer.from("x") });

    await page.locator("#extraction-test-run-btn").click();

    await expect(page.locator("#extraction-test-results")).not.toHaveClass(/hidden/);
    await expect(page.locator(".extraction-result-filename")).toHaveText("us-passport.jpg");
    await expect(page.locator(".extraction-result-time")).toContainText("13.9s");
    await expect(page.locator("#extraction-test-result-fields")).toContainText("Given Name");
    await expect(page.locator("#extraction-test-result-fields")).toContainText("WHITNEY");
  });

  test("shows error message when POST fails", async ({ page }) => {
    await page.route("**/v1/admin/extraction-test", (route) => {
      if (route.request().method() === "POST") {
        route.fulfill({ status: 422, json: { detail: "Invalid file type" } });
      } else {
        route.continue();
      }
    });
    await page.route("**/v1/admin/documents**", (route) =>
      route.fulfill({ json: { documents: [] } }),
    );

    await page.goto("/");
    await page.evaluate(() => {
      const payload = btoa(
        JSON.stringify({ "cognito:groups": ["super-admin"], email: "admin@test.com" }),
      );
      const fakeToken = `h.${payload}.s`;
      sessionStorage.setItem(
        "docai_console_session",
        JSON.stringify({
          accessToken: "fake-at",
          idToken: fakeToken,
          refreshToken: "fake-rt",
          email: "admin@test.com",
          expiresAt: Date.now() + 3600000,
        }),
      );
    });
    await page.goto("/");
    await expect(page.locator("#view-title")).toHaveText("Manage API Keys");

    await navigateToRunner(page);
    await page.route("**/v1/admin/tenants**", (route) =>
      route.fulfill({
        json: { tenants: [{ tenantId: "e2e-test-tenant-gw0", displayName: "E2E Tenant" }] },
      }),
    );
    await selectTenant(page);
    await page
      .locator("#extraction-test-file")
      .setInputFiles({ name: "bad.xyz", mimeType: "application/octet-stream", buffer: Buffer.from("x") });

    await page.locator("#extraction-test-run-btn").click();

    await expect(page.locator("#extraction-test-status")).toContainText("Invalid file type");
    await expect(page.locator("#extraction-test-status")).toHaveClass(/extraction-test-error/);
  });

  test("tenant change clears results", async ({ page }) => {
    await setup(page);
    await navigateToRunner(page);
    await page.route("**/v1/admin/tenants**", (route) =>
      route.fulfill({
        json: {
          tenants: [
            { tenantId: "e2e-test-tenant-gw0", displayName: "E2E Tenant" },
            { tenantId: "other-tenant", displayName: "Other Tenant" },
          ],
        },
      }),
    );
    await selectTenant(page);
    await page
      .locator("#extraction-test-file")
      .setInputFiles({ name: "us-passport.jpg", mimeType: "image/jpeg", buffer: Buffer.from("x") });
    await page.locator("#extraction-test-run-btn").click();
    await expect(page.locator("#extraction-test-results")).not.toHaveClass(/hidden/);

    await selectTenant(page, "other-tenant");

    await expect(page.locator("#extraction-test-results")).toHaveClass(/hidden/);
    await expect(page.locator("#extraction-test-empty")).not.toHaveClass(/hidden/);
  });
});
