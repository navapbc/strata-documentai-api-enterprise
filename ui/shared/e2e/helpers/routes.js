/**
 * Shared Playwright route helpers for e2e-video recording specs.
 *
 * Each function registers one logical API surface on `page` and returns
 * immediately (no await needed at the call site — page.route is synchronous).
 */

const CONFIG_RESPONSE = {
  api_endpoint: { value: "https://api.admin.local" },
  cognito_user_pool_id: { value: "us-east-1_ADMIN0000" },
  cognito_client_id: { value: "adminclientid000000000000" },
  cognito_domain: { value: null },
  cognito_google_enabled: { value: false },
};

function json(body) {
  return {
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(body),
  };
}

/**
 * Mocks config.json with dummy Cognito config (no Google SSO).
 */
export function registerConfig(page) {
  page.route("**/config.json", (route) => route.fulfill(json(CONFIG_RESPONSE)));
}

/**
 * Mocks /v1/admin/tenants.
 *
 * @param {import('@playwright/test').Page} page
 * @param {object[]} tenants - array of tenant objects for the list response
 * @param {Record<string, object>} [byId] - optional map of tenantId -> detail
 *   object for GET /tenants/:id requests. When omitted, all requests are
 *   answered with the list response.
 */
export function registerTenants(page, tenants, byId = {}) {
  page.route("**/v1/admin/tenants**", (route) => {
    const url = route.request().url();
    for (const [id, detail] of Object.entries(byId)) {
      if (url.includes(`/tenants/${id}`)) {
        return route.fulfill(json(detail));
      }
    }
    return route.fulfill(json({ tenants }));
  });
}

/**
 * Sets a super-admin session in sessionStorage and navigates to "/".
 *
 * When privacyMode is true, the login page is shown first so the checkbox
 * tick is visible in the recording before the session is injected.
 *
 * @param {import('@playwright/test').Page} page
 * @param {{ privacyMode?: boolean }} [opts]
 */
export async function loginAs(page, { privacyMode = false } = {}) {
  const payload = btoa(
    JSON.stringify({
      "cognito:groups": ["super-admin"],
      email: "admin@example.com",
    }),
  );
  await page.goto("/");
  await page.evaluate(() => sessionStorage.clear());
  await page.goto("/");
  await page.locator("#sign-in-email").fill("admin@example.com");
  await page.locator("#sign-in-password").fill("••••••••••••");
  if (privacyMode) {
    await page.locator("#privacy-mode-checkbox + .toggle-track").click();
  }
  await page.evaluate(
    ([p, pm]) => {
      sessionStorage.setItem(
        "documentai_console_session",
        JSON.stringify({
          accessToken: "fake-at",
          idToken: `h.${p}.s`,
          refreshToken: "fake-rt",
          email: "admin@example.com",
          expiresAt: Date.now() + 3600000,
        }),
      );
      if (pm) {
        sessionStorage.setItem("privacy_mode", "true");
      } else {
        sessionStorage.removeItem("privacy_mode");
      }
    },
    [payload, privacyMode],
  );
  await page.goto("/");
}
