import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

let BlueprintEditor, Store, mockRulesGet, mockRulesPut, mockGetTenantId;

describe("blueprint-editor pane", () => {
  let root;

  beforeEach(async () => {
    vi.resetModules();

    mockRulesGet = vi
      .fn()
      .mockResolvedValue({ rules: [{ requiredFields: ["ssn"], optionalFields: ["name"] }] });
    mockRulesPut = vi.fn().mockResolvedValue({});
    mockGetTenantId = vi.fn().mockReturnValue("acme");

    vi.doMock("../../src/services/rules.js", () => ({
      get: mockRulesGet,
      put: mockRulesPut,
    }));
    vi.doMock("../../src/utils/tenant-context.js", () => ({
      getTenantId: mockGetTenantId,
      onChange: vi.fn((_cb) => () => {}),
    }));
    vi.doMock("../../src/utils/toast.js", () => ({ show: vi.fn() }));
    vi.doMock("../../src/utils/helpers.js", () => ({
      esc: (s) => s,
      formatDate: (d) => d,
      showLoading: vi.fn(),
      setViewActions: vi.fn(),
      clearViewActions: vi.fn(),
    }));

    Store = await import("../../src/state/blueprint-store.js");
    BlueprintEditor = await import("../../src/panes/blueprint-editor.js");

    root = document.createElement("div");
    document.body.appendChild(root);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    Store.reset();
  });

  it("mounts with title and save/discard buttons", () => {
    BlueprintEditor.mount(root);
    expect(root.querySelector("#bp-editor-title").textContent).toBe("Select a blueprint");
    expect(root.querySelector("#bp-save-btn")).toBeTruthy();
    expect(root.querySelector("#bp-discard-btn")).toBeTruthy();
  });

  it("renders empty state when no activeDocType", () => {
    BlueprintEditor.mount(root);
    expect(root.querySelector(".empty-state").textContent).toBe(
      "Select a document type from the list.",
    );
  });

  it("renders fields when activeDocType is set", () => {
    BlueprintEditor.mount(root);
    Store.set({
      schemas: {
        W2: [
          { name: "ssn", type: "string" },
          { name: "wages", type: "number" },
        ],
      },
      activeDocType: "W2",
      tenantId: "acme",
      rules: { ssn: "required" },
    });

    const rows = root.querySelectorAll(".field-row");
    expect(rows.length).toBe(2);
    expect(root.querySelector("#bp-editor-title").textContent).toBe("W2");
  });

  it("save button disabled when not dirty", () => {
    BlueprintEditor.mount(root);
    Store.set({
      schemas: { W2: [{ name: "ssn" }] },
      activeDocType: "W2",
      tenantId: "acme",
      dirty: false,
    });
    expect(root.querySelector("#bp-save-btn").disabled).toBe(true);
  });

  it("save button enabled when dirty and tenant set", () => {
    BlueprintEditor.mount(root);
    Store.set({
      schemas: { W2: [{ name: "ssn" }] },
      activeDocType: "W2",
      tenantId: "acme",
      dirty: true,
    });
    expect(root.querySelector("#bp-save-btn").disabled).toBe(false);
  });

  it("toggling a field sets dirty in store", () => {
    BlueprintEditor.mount(root);
    Store.set({
      schemas: { W2: [{ name: "ssn" }] },
      activeDocType: "W2",
      tenantId: "acme",
      rules: {},
    });

    const radio = root.querySelector('input[value="required"]');
    radio.checked = true;
    radio.dispatchEvent(new Event("change"));

    expect(Store.get().dirty).toBe(true);
    expect(Store.get().rules.ssn).toBe("required");
  });

  it("save calls RulesService.put and clears dirty", async () => {
    BlueprintEditor.mount(root);
    Store.set({
      schemas: { W2: [{ name: "ssn" }] },
      activeDocType: "W2",
      tenantId: "acme",
      rules: { ssn: "required" },
      dirty: true,
    });

    root.querySelector("#bp-save-btn").click();
    await new Promise((r) => setTimeout(r, 0));

    expect(mockRulesPut).toHaveBeenCalledWith("acme", "W2", ["ssn"], []);
    expect(Store.get().dirty).toBe(false);
  });

  it("loads rules when tenant+docType change", async () => {
    BlueprintEditor.mount(root);
    Store.set({ schemas: { W2: [{ name: "ssn" }] }, activeDocType: "W2", tenantId: "acme" });

    // Wait for async loadRules
    await new Promise((r) => setTimeout(r, 0));
    expect(mockRulesGet).toHaveBeenCalledWith("acme", "W2");
  });
});
