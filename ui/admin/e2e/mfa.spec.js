import { test, expect } from "@playwright/test";

test.describe("MFA flow", () => {
  test("MFA card elements exist in login template", async ({ page }) => {
    await page.goto("/");
    // MFA cards should exist but be hidden
    await expect(page.locator("#mfa-card")).toBeHidden();
    await expect(page.locator("#mfa-setup-card")).toBeHidden();
    await expect(page.locator("#mfa-code")).toBeHidden();
    await expect(page.locator("#mfa-setup-code")).toBeHidden();
  });

  test("sign-up flow shows confirm card", async ({ page }) => {
    await page.goto("/");
    await page.click("#show-sign-up");
    await expect(page.locator("#sign-up-card")).toBeVisible();
    await expect(page.locator("#sign-up-email")).toBeVisible();
    await expect(page.locator("#sign-up-password")).toBeVisible();
    await expect(page.locator("#sign-up-password-confirm")).toBeVisible();
  });

  test("password toggle works", async ({ page }) => {
    await page.goto("/");
    const input = page.locator("#sign-in-password");
    const toggle = page.locator('.show-password[data-target="sign-in-password"]');

    await expect(input).toHaveAttribute("type", "password");
    await toggle.click();
    await expect(input).toHaveAttribute("type", "text");
    await toggle.click();
    await expect(input).toHaveAttribute("type", "password");
  });
});
