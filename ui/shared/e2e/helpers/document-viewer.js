export const SELECTORS = {
  tenantSelect: "#tenant-select",
  detailPane: "#doc-pane-detail",
  previewPane: "#doc-pane-preview",
  bboxOverlay: "#doc-pane-preview .bbox-overlay rect",
  fieldRows: "#doc-pane-detail tr[data-field]",
};

/**
 * Hover each field row in sequence to demonstrate the bbox highlight linking.
 *
 * @param {import('@playwright/test').Page} page
 * @param {string[]} fieldNames - data-field attribute values to hover
 * @param {string} [rowSelector] - base selector for field rows
 * @param {number} [pauseMs] - pause between hovers
 */
export async function hoverFields(
  page,
  fieldNames,
  rowSelector = "tr[data-field]",
  pauseMs = 800,
) {
  for (const name of fieldNames) {
    await page
      .locator(
        `${rowSelector.replace("[data-field]", "")}[data-field="${name}"]`,
      )
      .hover();
    await page.waitForTimeout(pauseMs);
  }
}

/**
 * Wait for the bbox overlay to be visible and assert at least one rect exists.
 *
 * @param {import('@playwright/test').Page} page
 * @param {Function} expect
 * @param {string} [overlaySelector]
 */
export async function expectBboxOverlay(
  page,
  expect,
  overlaySelector = ".bbox-overlay rect",
) {
  const rects = page.locator(overlaySelector);
  await expect(rects.first()).toBeVisible();
  expect(await rects.count()).toBeGreaterThan(0);
}
