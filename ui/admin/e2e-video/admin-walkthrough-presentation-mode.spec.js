import { test, expect } from "@playwright/test";
import { TENANTS, USAGE_RESP } from "../../shared/e2e/fixtures/recording/admin-data.js";
import { registerConfig, registerTenants, loginAs } from "../../shared/e2e/helpers/routes.js";

// ---------------------------------------------------------------------------
// Scripted demo video: Presentation Mode toggle.
//
// Flow: login page -> tick presentation mode checkbox -> login -> Usage (masked)
//
// All network dependencies are mocked - runs offline, no credentials needed.
// ---------------------------------------------------------------------------

test("presentation mode walkthrough", async ({ page }) => {
  const json = (body) => ({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(body),
  });

  registerConfig(page);
  registerTenants(page, TENANTS);
  await page.route("**/v1/admin/usage**", (route) =>
    route.fulfill(json(USAGE_RESP)),
  );

  const goToUsage = async () => {
    await page.locator('[data-section="reporting"]').click();
    await expect(page.locator("#section-reporting")).not.toHaveClass(/hidden/);
    await page.locator('a.nav-item[data-view="usage"]').click();
    await expect(page.locator("#view-title")).toHaveText(/^Usage Tracking/);
    await expect(page.locator(".usage-table")).toBeVisible({ timeout: 10000 });
  };

  // === 1. Tick presentation mode on login page, then log in ====================
  await test.step("Enable presentation mode and log in", async () => {
    await loginAs(page, { presentationMode: true });
    await expect(page.locator("#view-title")).toHaveText("Home");
  });

  // === 2. Navigate to Usage — masked data + banner visible ================
  await test.step("Usage - masked data", async () => {
    await goToUsage();
    await expect(page.locator(".info-banner")).toBeVisible();
    await page.waitForTimeout(2000);
  });
});
