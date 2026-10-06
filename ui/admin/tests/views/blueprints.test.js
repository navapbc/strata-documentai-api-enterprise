import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { buildTenant } from "../factories.js";

const SCHEMAS = [
  { documentType: "W2", description: "W2 Form", category: "employer_income", fieldCount: 5 },
  { documentType: "1099", description: "1099 Form", category: "employer_income", fieldCount: 3 },
  { documentType: "Payslip", description: "Pay Slip", category: "employer_income", fieldCount: 2 },
];

async function flush() {
  for (let i = 0; i < 5; i++) {
    await new Promise((r) => setTimeout(r, 0));
  }
}

async function setup({ tenantId = null, tenant = null } = {}) {
  vi.resetModules();

  const mockListSchemas = vi.fn().mockResolvedValue({ schemas: SCHEMAS });
  const mockGetTenant = vi.fn().mockResolvedValue(tenant ?? buildTenant());
  const mockUpdate = vi.fn().mockResolvedValue(buildTenant());
  const mockToast = { show: vi.fn() };

  vi.doMock("../../src/services/schemas.js", () => ({ list: mockListSchemas }));
  vi.doMock("../../src/services/tenants.js", () => ({ get: mockGetTenant, update: mockUpdate }));
  vi.doMock("../../src/utils/tenant-context.js", () => ({
    getTenantId: vi.fn(() => tenantId),
    onChange: vi.fn(() => () => {}),
    mountSelect: vi.fn(),
    unmountSelect: vi.fn(),
  }));
  vi.doMock("../../src/utils/toast.js", () => mockToast);

  const View = await import("../../src/views/blueprints/blueprints.js");
  return { View, mockListSchemas, mockGetTenant, mockUpdate, mockToast };
}

describe("blueprints view", () => {
  let root;

  beforeEach(() => {
    root = document.createElement("div");
    document.body.appendChild(root);
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  // --- Mount / load ---

  it("mounts and loads schemas", async () => {
    const { View, mockListSchemas } = await setup();
    View.mount(root);
    await flush();
    expect(mockListSchemas).toHaveBeenCalled();
  });

  it("renders a row per schema", async () => {
    const { View } = await setup();
    View.mount(root);
    await flush();
    expect(root.querySelectorAll("#blueprints-tbody tr").length).toBe(SCHEMAS.length);
  });

  it("loads tenant when tenant is selected", async () => {
    const { View, mockGetTenant } = await setup({ tenantId: "acme-corp" });
    View.mount(root);
    await flush();
    expect(mockGetTenant).toHaveBeenCalledWith("acme-corp");
  });

  // --- Toggle state ---

  it("all checkboxes checked when no disabledBlueprintList", async () => {
    const { View } = await setup({
      tenantId: "acme-corp",
      tenant: buildTenant({ disabledBlueprintList: null }),
    });
    View.mount(root);
    await flush();

    root.querySelectorAll("input[type=checkbox]").forEach((cb) => expect(cb.checked).toBe(true));
  });

  it("disabled blueprints render unchecked", async () => {
    const { View, mockGetTenant } = await setup({
      tenantId: "acme-corp",
      tenant: buildTenant({ disabledBlueprintList: ["1099"] }),
    });
    View.mount(root);
    await flush();

    expect(mockGetTenant).toHaveBeenCalledWith("acme-corp");
    // Trigger a re-render to ensure _disabledSet is applied
    root.querySelector("#blueprints-search").dispatchEvent(new Event("input"));

    const rows = root.querySelectorAll("#blueprints-tbody tr");
    // W2 enabled, 1099 disabled, Payslip enabled
    expect(rows[0].querySelector("input").checked).toBe(true);
    expect(rows[1].querySelector("input").checked).toBe(false);
    expect(rows[2].querySelector("input").checked).toBe(true);
  });

  // --- Toggle interaction ---

  it("unchecking a blueprint adds it to disabledBlueprintList", async () => {
    const { View, mockUpdate } = await setup({
      tenantId: "acme-corp",
      tenant: buildTenant({ disabledBlueprintList: null }),
    });
    View.mount(root);
    await flush();

    const w2Checkbox = root.querySelectorAll("#blueprints-tbody input")[0];
    w2Checkbox.checked = false;
    w2Checkbox.dispatchEvent(new Event("change"));
    await flush();

    expect(mockUpdate).toHaveBeenCalledWith("acme-corp", { disabledBlueprintList: ["W2"] });
  });

  it("re-checking a blueprint removes it from disabledBlueprintList", async () => {
    const { View, mockUpdate } = await setup({
      tenantId: "acme-corp",
      tenant: buildTenant({ disabledBlueprintList: ["W2"] }),
    });
    View.mount(root);
    await flush();

    const w2Checkbox = root.querySelectorAll("#blueprints-tbody input")[0];
    w2Checkbox.checked = true;
    w2Checkbox.dispatchEvent(new Event("change"));
    await flush();

    expect(mockUpdate).toHaveBeenCalledWith("acme-corp", { disabledBlueprintList: [] });
  });

  it("re-enabling last disabled blueprint sends []", async () => {
    const { View, mockUpdate } = await setup({
      tenantId: "acme-corp",
      tenant: buildTenant({ disabledBlueprintList: ["1099"] }),
    });
    View.mount(root);
    await flush();

    const checkbox1099 = root.querySelectorAll("#blueprints-tbody input")[1];
    checkbox1099.checked = true;
    checkbox1099.dispatchEvent(new Event("change"));
    await flush();

    expect(mockUpdate).toHaveBeenCalledWith("acme-corp", { disabledBlueprintList: [] });
  });

  it("shows toast and reverts on update failure", async () => {
    const { View, mockUpdate, mockToast } = await setup({
      tenantId: "acme-corp",
      tenant: buildTenant({ disabledBlueprintList: null }),
    });
    mockUpdate.mockRejectedValue(new Error("Server error"));
    View.mount(root);
    await flush();

    const w2Checkbox = root.querySelectorAll("#blueprints-tbody input")[0];
    w2Checkbox.checked = false;
    w2Checkbox.dispatchEvent(new Event("change"));
    await flush();

    expect(mockToast.show).toHaveBeenCalledWith("Server error");
  });

  // --- Search ---

  it("filters rows by search query", async () => {
    const { View } = await setup();
    View.mount(root);
    await flush();

    root.querySelector("#blueprints-search").value = "w2";
    root.querySelector("#blueprints-search").dispatchEvent(new Event("input"));

    expect(root.querySelectorAll("#blueprints-tbody tr").length).toBe(1);
  });

  // --- Unmount ---

  it("unmount clears root", async () => {
    const { View } = await setup();
    View.mount(root);
    View.unmount(root);
    expect(root.children.length).toBe(0);
  });
});
