import { describe, it, expect, afterEach, vi } from "vitest";
import { _fillDailyGaps } from "../../src/views/usage/usage.js";

describe("_fillDailyGaps", () => {
  it("fills all days for a past month with zeros", () => {
    const result = _fillDailyGaps("2026-01", []);
    expect(result.length).toBe(31);
    expect(result[0].date).toBe("2026-01-01");
    expect(result[30].date).toBe("2026-01-31");
    expect(result[0].totalRecords).toBe(0);
  });

  it("handles February (non-leap year)", () => {
    const result = _fillDailyGaps("2027-02", []);
    expect(result.length).toBe(28);
  });

  it("handles February (leap year)", () => {
    const result = _fillDailyGaps("2028-02", []);
    expect(result.length).toBe(29);
  });

  it("overlays existing data onto zero-filled days", () => {
    const existing = [
      {
        date: "2026-03-05",
        totalRecords: 10,
        totalBdaPages: 8,
        totalFileSizeBytes: 5000,
        totalBedrockInputTokens: 100,
        totalBedrockOutputTokens: 50,
      },
    ];
    const result = _fillDailyGaps("2026-03", existing);
    expect(result.length).toBe(31);
    expect(result[4].date).toBe("2026-03-05");
    expect(result[4].totalRecords).toBe(10);
    expect(result[3].totalRecords).toBe(0);
  });

  it("stops at today for current month", () => {
    const now = new Date();
    const month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    const result = _fillDailyGaps(month, []);
    expect(result.length).toBe(now.getDate());
  });

  it("shows all days for a past month", () => {
    const result = _fillDailyGaps("2026-04", []);
    expect(result.length).toBe(30);
    expect(result[29].date).toBe("2026-04-30");
  });
});

const USAGE_DATA = {
  tenants: [{ tenantId: "test-tenant-id", maskedTenantId: "m-1", totalRecords: 5 }],
};

async function mountUsageView({ presentationMode }) {
  vi.resetModules();
  if (presentationMode) {
    sessionStorage.setItem("presentation_mode", "true");
  } else {
    sessionStorage.removeItem("presentation_mode");
  }
  vi.doMock("../../src/services/usage.js", () => ({
    get: vi.fn().mockResolvedValue(USAGE_DATA),
  }));
  vi.doMock("../../src/utils/tenant-context.js", () => ({
    getTenantId: vi.fn(() => null),
    onChange: vi.fn(() => () => {}),
    mountSelect: vi.fn(),
    unmountSelect: vi.fn(),
  }));
  vi.doMock("../../src/utils/toast.js", () => ({ show: vi.fn() }));
  const UsageView = await import("../../src/views/usage/usage.js");
  const root = document.createElement("div");
  document.body.appendChild(root);
  UsageView.mount(root);
  await new Promise((r) => setTimeout(r, 0));
  return root;
}

describe("usage view - download button visibility", () => {
  afterEach(() => {
    document.body.innerHTML = "";
    sessionStorage.clear();
  });

  it("is visible and enabled without presentation mode", async () => {
    const root = await mountUsageView({ presentationMode: false });
    const btn = root.querySelector("#usage-download-btn");
    expect(btn.classList.contains("hidden")).toBe(false);
    expect(btn.disabled).toBe(false);
  });

  it("is hidden and disabled with presentation mode", async () => {
    const root = await mountUsageView({ presentationMode: true });
    const btn = root.querySelector("#usage-download-btn");
    expect(btn.classList.contains("hidden")).toBe(true);
    expect(btn.disabled).toBe(true);
  });
});
