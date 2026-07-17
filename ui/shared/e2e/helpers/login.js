/**
 * Mock Cognito routes and perform login + MFA.
 *
 * @param {import('@playwright/test').Page} page
 * @param {object} [opts]
 * @param {string} [opts.email]
 * @param {string} [opts.password]
 * @param {string} [opts.session]
 * @param {string[]} [opts.groups]
 * @param {Function} [opts.expect]
 */
export async function loginWithMfa(page, {
  email = "admin@example.com",
  password = "AdminPassword123!",
  session = "session-token",
  groups = ["super-admin"],
  expect,
} = {}) {
  const json = (body) => ({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(body),
  });

  await page.route(/cognito-idp\./, async (route) => {
    const target = route.request().headers()["x-amz-target"] || "";
    if (target.includes("InitiateAuth")) {
      return route.fulfill(json({ ChallengeName: "SOFTWARE_TOKEN_MFA", Session: session }));
    }
    if (target.includes("RespondToAuthChallenge")) {
      const payload = btoa(JSON.stringify({ "cognito:groups": groups, email }));
      return route.fulfill(json({
        AuthenticationResult: {
          AccessToken: "access-token",
          IdToken: `h.${payload}.s`,
          RefreshToken: "refresh-token",
          ExpiresIn: 3600,
        },
      }));
    }
    return route.fulfill(json({}));
  });

  await expect(page.locator("#sign-in-card")).toBeVisible();
  await page.fill("#sign-in-email", email);
  await page.fill("#sign-in-password", password);
  await page.waitForTimeout(600);
  await page.click('#sign-in-form button[type="submit"]');

  await expect(page.locator("#mfa-card")).toBeVisible();
  await page.fill("#mfa-code", "123456");
  await page.waitForTimeout(500);
  await page.click('#mfa-form button[type="submit"]');
}
