import { test, expect } from "@playwright/test";

async function loginAsAdmin(page) {
  await page.goto("/");
  await page.evaluate(() => {
    const payload = btoa(
      JSON.stringify({ "cognito:groups": ["super-admin"], email: "admin@test.com" }),
    );
    const fakeToken = `h.${payload}.s`;
    const session = {
      accessToken: "fake-at",
      idToken: fakeToken,
      refreshToken: "fake-rt",
      email: "admin@test.com",
      expiresAt: Date.now() + 3600000,
    };
    sessionStorage.setItem("docai_console_session", JSON.stringify(session));
  });
  await page.goto("/");
}

async function navigateToDocuments(page, view = "documents") {
  await page.locator('[data-section="docs"]').click();
  await expect(page.locator("#section-docs")).toBeVisible();
  await page.locator(`[data-view="${view}"]`).click({ force: true });
}

test.describe("Recent Documents", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
    await expect(page.locator("#view-title")).toHaveText("Manage API Keys");
  });

  test("mounts recent documents view", async ({ page }) => {
    await navigateToDocuments(page, "documents");
    await expect(page.locator("#documents-list")).toBeAttached();
    await expect(page.locator("#document-status-filter")).toBeVisible();
  });

  test("shows tenant prompt when no tenant selected", async ({ page }) => {
    await navigateToDocuments(page, "documents");
    await expect(page.locator("#no-documents")).toContainText("Select a tenant");
  });

  test("has status filter dropdown", async ({ page }) => {
    await navigateToDocuments(page, "documents");
    const select = page.locator("#document-status-filter");
    await expect(select).toBeVisible();
    await expect(select.locator("option")).toHaveCount(11);
  });

  test("preview panel shows empty state", async ({ page }) => {
    await navigateToDocuments(page, "documents");
    await expect(page.locator("#document-preview-panel")).toContainText(
      "Select a document to preview",
    );
  });

  test("detail panel starts collapsed", async ({ page }) => {
    await navigateToDocuments(page, "documents");
    await expect(page.locator("#document-detail-panel")).toHaveClass(/collapsed/);
  });

  test("tenant filter bar is visible", async ({ page }) => {
    await navigateToDocuments(page, "documents");
    await expect(page.locator(".tenant-filter-bar")).toBeVisible();
  });
});

test.describe.skip("Search Documents", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
    await expect(page.locator("#view-title")).toHaveText("Manage API Keys");
  });

  test("mounts search documents view", async ({ page }) => {
    await navigateToDocuments(page, "document-search");
    await expect(page.locator("#documents-list")).toBeAttached();
    await expect(page.locator("#document-search-input")).toBeVisible();
    await expect(page.locator("#document-search-btn")).toBeVisible();
  });

  test("shows search prompt initially", async ({ page }) => {
    await navigateToDocuments(page, "document-search");
    await expect(page.locator("#no-documents")).toContainText("Search for documents");
  });

  test("search input accepts text", async ({ page }) => {
    await navigateToDocuments(page, "document-search");
    const input = page.locator("#document-search-input");
    await input.fill("test-document.pdf");
    await expect(input).toHaveValue("test-document.pdf");
  });

  test("has status filter dropdown", async ({ page }) => {
    await navigateToDocuments(page, "document-search");
    const select = page.locator("#document-status-filter");
    await expect(select).toBeVisible();
    await expect(select.locator("option")).toHaveCount(11);
  });

  test("preview panel shows empty state", async ({ page }) => {
    await navigateToDocuments(page, "document-search");
    await expect(page.locator("#document-preview-panel")).toContainText(
      "Select a document to preview",
    );
  });

  test("detail panel starts collapsed", async ({ page }) => {
    await navigateToDocuments(page, "document-search");
    await expect(page.locator("#document-detail-panel")).toHaveClass(/collapsed/);
  });
});
