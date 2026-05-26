import { test, expect } from "@playwright/test";

// Helper: inject a fake session so we bypass login
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

test.describe("Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
    // Wait for dashboard to fully initialize (default view title set)
    await expect(page.locator("#view-title")).toHaveText("API Keys");
  });

  test("dashboard renders sidebar and main content", async ({ page }) => {
    await expect(page.locator(".sidebar")).toBeVisible();
    await expect(page.locator("#main-content")).toBeVisible();
    await expect(page.locator("#view-title")).toBeVisible();
  });

  test("default view is API Keys", async ({ page }) => {
    await expect(page.locator("#view-title")).toHaveText("API Keys");
    await expect(page.locator("#keys-table")).toBeVisible();
  });

  test("clicking nav items changes view title", async ({ page }) => {
    await page.locator('[data-section="tenants"]').click();
    await expect(page.locator("#section-tenants")).toBeVisible();
    await page.locator('[data-view="tenants"]').click({ force: true });
    await expect(page.locator("#view-title")).toHaveText("Manage Tenants");
  });

  test("clicking users nav changes title", async ({ page }) => {
    await page.locator('[data-section="users"]').click();
    await expect(page.locator("#section-users")).toBeVisible();
    await page.locator('[data-view="users"]').click({ force: true });
    await expect(page.locator("#view-title")).toHaveText("Manage Users");
  });

  test("clicking nav items mounts correct content", async ({ page }) => {
    await expect(page.locator("#keys-tbody")).toBeAttached();

    await page.locator('[data-section="docs"]').click();
    await expect(page.locator("#section-docs")).toBeVisible();
    await page.locator('[data-view="documents"]').click({ force: true });
    await expect(page.locator("#documents-tbody")).toBeAttached();
  });

  test("view actions update on navigation", async ({ page }) => {
    await expect(page.locator("#view-actions button").first()).toContainText("+ Create Key");

    await page.locator('[data-section="tenants"]').click();
    await expect(page.locator("#section-tenants")).toBeVisible();
    await page.locator('[data-view="tenants"]').click({ force: true });
    await expect(page.locator("#view-actions button").first()).toContainText("+ Create Tenant");
  });

  test("previous view is unmounted on navigation", async ({ page }) => {
    await expect(page.locator("#keys-table")).toBeVisible();

    await page.locator('[data-section="tenants"]').click();
    await expect(page.locator("#section-tenants")).toBeVisible();
    await page.locator('[data-view="tenants"]').click({ force: true });
    await expect(page.locator("#keys-table")).not.toBeAttached();
    await expect(page.locator("#tenants-table")).toBeVisible();
  });

  test("super-admin sees Users and Tenants nav sections", async ({ page }) => {
    await expect(page.locator("#nav-section-users")).toBeVisible();
    await expect(page.locator("#nav-section-tenants")).toBeVisible();
  });

  test("sidebar sections expand on click", async ({ page }) => {
    const section = page.locator('[data-section="docs"]');
    await section.click();
    await expect(page.locator("#section-docs")).toBeVisible();
  });

  test("logout clears session and shows login", async ({ page }) => {
    await page.click("#logout-btn");
    await expect(page.locator("#sign-in-form")).toBeVisible();
  });
});
