import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { test, expect } from "@playwright/test";
import { METRICS_RESP } from "../../shared/e2e/fixtures/recording/admin-data.js";
import { registerConfig, registerTenants, loginAs } from "../../shared/e2e/helpers/routes.js";

// ---------------------------------------------------------------------------
// Trailer, clips 2 and 3 (admin console), recorded as separate videos:
//   - "rules":   beat 3 (~15s) - required fields defined for the Pay Stub type
//   - "metrics": beat 4 (~10s) - operational monitoring (processing timing)
//
// Mocked offline like e2e-video/; kept in e2e-trailer/ so `make record-ui`
// ignores it. Record with: npx playwright test --config=playwright.trailer.config.js
// ---------------------------------------------------------------------------

const TENANT_ID = "acme-corp";

const FIELDS = [
  { name: "employerName", documentType: "Pay Stub", type: "string" },
  { name: "employeeName", documentType: "Pay Stub", type: "string" },
  { name: "employeeId", documentType: "Pay Stub", type: "string" },
  { name: "payPeriod", documentType: "Pay Stub", type: "string" },
  { name: "grossPay", documentType: "Pay Stub", type: "currency" },
  { name: "netPay", documentType: "Pay Stub", type: "currency" },
];

const PAY_STUB_RULES = {
  rules: [
    {
      requiredFields: ["grossPay", "payPeriod"],
      optionalFields: ["employerName", "employeeName", "employeeId", "netPay"],
    },
  ],
};

// The timing chart reads dailyStats[].timingStats.*, but the shared fixture
// carries those values flat on each day, so the chart renders empty. Reshape
// here rather than change the shared fixture used by the GIF walkthroughs.
const METRICS = {
  ...METRICS_RESP,
  dailyStats: METRICS_RESP.dailyStats.map((d) => ({
    ...d,
    timingStats: {
      bdaProcessingTimeAvg: d.bdaProcessingTimeAvg,
      bdaWaitTimeAvg: +(d.totalProcessingTimeAvg - d.bdaProcessingTimeAvg).toFixed(1),
      totalProcessingTimeAvg: d.totalProcessingTimeAvg,
    },
  })),
};

// Each clip records its own sign-in. Save when the app is ready (Home visible)
// so the assembler can start the clip there instead of on the login screen.
// The video starts at context creation, slightly before the test body.
const MARKS = "video-output/trailer-admin-marks.json";
function saveMark(key, startedAt) {
  mkdirSync("video-output", { recursive: true });
  const marks = existsSync(MARKS) ? JSON.parse(readFileSync(MARKS, "utf8")) : {};
  marks[key] = (Date.now() - startedAt) / 1000;
  writeFileSync(MARKS, JSON.stringify(marks));
}

const json = (body) => ({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify(body),
});

test("rules: required fields for a document type", async ({ page }) => {
  const startedAt = Date.now();
  registerConfig(page);
  registerTenants(
    page,
    [{ tenantId: TENANT_ID, displayName: "Acme Corporation", isActive: true }],
    {
      [TENANT_ID]: {
        tenantId: TENANT_ID,
        displayName: "Acme Corporation",
        isActive: true,
        disabled_blueprint_list: [],
      },
    },
  );
  await page.route("**/v1/dictionary/**", (route) => route.fulfill(json({ fields: [] })));
  await page.route("**/v1/dictionary/fields*", (route) => route.fulfill(json({ fields: FIELDS })));
  await page.route("**/v1/config/extraction-rules**", (route) => {
    if (route.request().method() === "PUT") return route.fulfill(json({ ok: true }));
    const docType = new URL(route.request().url()).searchParams.get("document_type") || "";
    return route.fulfill(json(docType === "Pay Stub" ? PAY_STUB_RULES : { rules: [] }));
  });
  await page.route("**/v1/audit/**", (route) => route.fulfill(json({})));

  await loginAs(page);
  await expect(page.locator("#view-title")).toHaveText("Home");
  saveMark("rules", startedAt);
  await page.waitForTimeout(300);

  await page.locator('[data-section="management"]').click();
  await expect(page.locator("#section-management")).not.toHaveClass(/hidden/);
  await page.locator('a.nav-item[data-view="extraction-rules"]').click();
  await expect(page.locator("#view-title")).toHaveText(/^Manage Extraction Rules/);
  await page.waitForTimeout(1200);
  await page.locator("#tenant-select").selectOption(TENANT_ID);
  await page.waitForTimeout(800);

  await page.locator("#bp-list-pane .combobox-input").clear();
  await page.locator("#bp-list-pane .combobox-input").click();
  await expect(page.locator("#bp-list-pane .combobox-option").first()).toBeVisible({
    timeout: 15000,
  });
  await page.locator("#bp-list-pane .combobox-option", { hasText: "Pay Stub" }).click();
  await expect(page.locator("#bp-fields-list h3")).toHaveText("Pay Stub");
  await expect(page.locator(".field-row").first()).toBeVisible();
  await page.waitForTimeout(3000);

  // Make employee ID required to show the change a configurator would make.
  await page
    .locator(".field-row")
    .filter({ hasText: "employeeId" })
    .locator('.toggle-label:has(input[value="required"])')
    .click();
  await page.waitForTimeout(2500);
  await page.locator("#bp-fields-list button.btn-primary").click();
  await page.waitForTimeout(2500);
});

test("metrics: operational monitoring", async ({ page }) => {
  const startedAt = Date.now();
  registerConfig(page);
  registerTenants(page, [{ tenantId: TENANT_ID, displayName: "Acme Corporation", isActive: true }]);
  await page.route("**/v1/metrics**", (route) => route.fulfill(json(METRICS)));
  await page.route("**/v1/audit/**", (route) => route.fulfill(json({})));

  await loginAs(page);
  await expect(page.locator("#view-title")).toHaveText("Home");
  saveMark("metrics", startedAt);
  await page.waitForTimeout(300);

  await page.locator('[data-section="reporting"]').click();
  await expect(page.locator("#section-reporting")).not.toHaveClass(/hidden/);
  await page.locator('a.nav-item[data-view="metrics"]').click();
  await expect(page.locator("#view-title")).toHaveText(/^Metrics Dashboard/);
  await expect(page.locator("#metrics-empty")).toHaveClass(/hidden/);
  await page.waitForTimeout(2200);
  await page.locator('.metrics-tab[data-tab="outcomes"]').click();
  await page.waitForTimeout(2500);
  await page.locator('.metrics-tab[data-tab="timing"]').click();
  await page.waitForTimeout(3000);
});
