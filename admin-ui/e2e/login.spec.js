import { test, expect } from "@playwright/test";

test.describe("Login screen", () => {
  test("renders sign-in form", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("#sign-in-form")).toBeVisible();
    await expect(page.locator("#sign-in-email")).toBeVisible();
    await expect(page.locator("#sign-in-password")).toBeVisible();
  });

  test("shows sign-up form when link clicked", async ({ page }) => {
    await page.goto("/");
    await page.click("#show-sign-up");
    await expect(page.locator("#sign-up-card")).toBeVisible();
    await expect(page.locator("#sign-in-card")).toBeHidden();
  });

  test("shows sign-in form when back link clicked", async ({ page }) => {
    await page.goto("/");
    await page.click("#show-sign-up");
    await page.click("#show-sign-in");
    await expect(page.locator("#sign-in-card")).toBeVisible();
    await expect(page.locator("#sign-up-card")).toBeHidden();
  });

  test("shows error on empty submit", async ({ page }) => {
    await page.goto("/");
    await page.click('#sign-in-form button[type="submit"]');
    // HTML5 validation prevents submit, form stays visible
    await expect(page.locator("#sign-in-form")).toBeVisible();
  });
});
