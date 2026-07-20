import { describe, it, expect, beforeEach, vi } from "vitest";
import * as Store from "../../src/state/blueprint-store.js";
import * as ExtractionRuleEditor from "../../src/panes/extraction-rule-editor.js";

// Mock modules before import
vi.mock("../../src/services/rules.js", () => ({
  get: vi
    .fn()
    .mockResolvedValue({ rules: [{ requiredFields: ["ssn"], optionalFields: ["name"] }] }),
  put: vi.fn().mockResolvedValue({}),
}));

vi.mock("../../src/utils/tenant-context.js", () => ({
  getTenantId: vi.fn(() => null),
  onChange: vi.fn(() => () => {}),
}));

vi.mock("../../src/utils/toast.js", () => ({
  show: vi.fn(),
}));

describe("extraction-rule-editor pane", () => {
  let root;

  beforeEach(() => {
    Store.reset();
    root = document.createElement("div");
    document.body.innerHTML =
      '<div id="view-actions"><button id="bp-save-btn"></button><button id="bp-discard-btn"></button></div>';
    document.body.appendChild(root);
  });

  it("renders empty state when no activeDocType", () => {
    Store.set({ schemasLoading: false, schemas: { W2: [] }, tenantId: "t" });
    ExtractionRuleEditor.mount(root);
    expect(root.textContent).toContain("Select a document type");
  });

  it("renders fields when activeDocType is set", () => {
    Store.set({
      schemasLoading: false,
      schemas: {
        W2: [
          { name: "ssn", type: "string" },
          { name: "wages", type: "number" },
        ],
      },
      activeDocType: "W2",
      tenantId: "test-tenant",
      rules: {},
    });
    ExtractionRuleEditor.mount(root);
    const fields = root.querySelectorAll(".field-name");
    expect(fields.length).toBe(2);
    expect(fields[0].textContent).toBe("ssn");
    expect(fields[1].textContent).toBe("wages");
  });

  it("renders radio toggles for each field", () => {
    Store.set({
      schemasLoading: false,
      schemas: { W2: [{ name: "ssn", type: "string" }] },
      activeDocType: "W2",
      tenantId: "test-tenant",
      rules: {},
    });
    ExtractionRuleEditor.mount(root);
    const radios = root.querySelectorAll('input[type="radio"]');
    expect(radios.length).toBe(3);
  });

  it("disables radios when no tenant selected", () => {
    Store.set({
      schemasLoading: false,
      schemas: { W2: [{ name: "ssn", type: "string" }] },
      activeDocType: "W2",
      tenantId: null,
      rules: {},
    });
    ExtractionRuleEditor.mount(root);
    const radios = root.querySelectorAll('input[type="radio"]');
    // Radios should exist but be disabled
    expect(radios.length).toBeGreaterThan(0);
    radios.forEach((r) => expect(r.disabled).toBe(true));
  });

  it("toggling a radio sets dirty in store", () => {
    Store.set({
      schemasLoading: false,
      schemas: { W2: [{ name: "ssn", type: "string" }] },
      activeDocType: "W2",
      tenantId: "test-tenant",
      rules: {},
    });
    ExtractionRuleEditor.mount(root);
    const required = root.querySelector('input[value="required"]');
    required.dispatchEvent(new Event("change"));
    expect(Store.get().dirty).toBe(true);
    expect(Store.get().rules.ssn).toBe("required");
  });
});

import * as RulesService from "../../src/services/rules.js";
import * as Toast from "../../src/utils/toast.js";

describe("extraction-rule-editor saveRules", () => {
  let root;

  beforeEach(() => {
    Store.reset();
    root = document.createElement("div");
    document.body.innerHTML =
      '<div id="view-actions"><button id="bp-save-btn"></button><button id="bp-discard-btn"></button></div>';
    document.body.appendChild(root);
    vi.clearAllMocks();
  });

  it("calls RulesService.put with correct fields on save", async () => {
    Store.set({
      schemasLoading: false,
      schemas: {
        W2: [
          { name: "ssn", type: "string" },
          { name: "wages", type: "number" },
        ],
      },
      activeDocType: "W2",
      tenantId: "acme",
      rules: { ssn: "required", wages: "optional" },
      dirty: true,
    });
    ExtractionRuleEditor.mount(root);

    // Click save button
    const saveBtn = document.querySelector("#bp-save-btn");
    saveBtn.click();

    // Wait for async
    await vi.waitFor(() => {
      expect(RulesService.put).toHaveBeenCalledWith("acme", "W2", ["ssn"], ["wages"]);
    });
  });

  it("sets dirty to false after save", async () => {
    Store.set({
      schemasLoading: false,
      schemas: { W2: [{ name: "ssn", type: "string" }] },
      activeDocType: "W2",
      tenantId: "acme",
      rules: { ssn: "required" },
      dirty: true,
    });
    ExtractionRuleEditor.mount(root);

    document.querySelector("#bp-save-btn").click();

    await vi.waitFor(() => {
      expect(Store.get().dirty).toBe(false);
    });
  });

  it("shows toast on save success", async () => {
    Store.set({
      schemasLoading: false,
      schemas: { W2: [{ name: "ssn", type: "string" }] },
      activeDocType: "W2",
      tenantId: "acme",
      rules: { ssn: "required" },
      dirty: true,
    });
    ExtractionRuleEditor.mount(root);

    document.querySelector("#bp-save-btn").click();

    await vi.waitFor(() => {
      expect(Toast.show).toHaveBeenCalledWith("Rules saved");
    });
  });

  it("shows error toast on save failure", async () => {
    RulesService.put.mockRejectedValueOnce(new Error("DDB error"));
    Store.set({
      schemasLoading: false,
      schemas: { W2: [{ name: "ssn", type: "string" }] },
      activeDocType: "W2",
      tenantId: "acme",
      rules: { ssn: "required" },
      dirty: true,
    });
    ExtractionRuleEditor.mount(root);

    document.querySelector("#bp-save-btn").click();

    await vi.waitFor(() => {
      expect(Toast.show).toHaveBeenCalledWith("Failed to save: DDB error");
    });
  });

  it("does not call put when no tenant", async () => {
    Store.set({
      schemasLoading: false,
      schemas: { W2: [{ name: "ssn", type: "string" }] },
      activeDocType: "W2",
      tenantId: null,
      rules: { ssn: "required" },
      dirty: true,
    });
    ExtractionRuleEditor.mount(root);

    document.querySelector("#bp-save-btn").click();
    await new Promise((r) => setTimeout(r, 10));

    expect(RulesService.put).not.toHaveBeenCalled();
  });
});

describe("extraction-rule-editor header", () => {
  let root;

  beforeEach(() => {
    Store.reset();
    root = document.createElement("div");
    document.body.innerHTML =
      '<div id="view-actions"><button id="bp-save-btn"></button><button id="bp-discard-btn"></button></div>';
    document.body.appendChild(root);
  });

  it("renders blueprint name as header when activeDocType set", () => {
    Store.set({
      schemas: { W2: [{ name: "ssn", type: "string" }] },
      activeDocType: "W2",
      tenantId: "test-tenant",
      rules: {},
    });
    ExtractionRuleEditor.mount(root);
    const header = root.querySelector(".fields-list-header");
    expect(header).toBeTruthy();
    expect(header.textContent).toBe("W2");
  });

  it("does not render header when no activeDocType", () => {
    Store.set({ schemas: { W2: [{ name: "ssn" }] }, tenantId: "t" });
    ExtractionRuleEditor.mount(root);
    expect(root.querySelector(".fields-list-header")).toBeFalsy();
  });
});

describe("extraction-rule-editor field defaults", () => {
  let root;

  beforeEach(() => {
    Store.reset();
    root = document.createElement("div");
    document.body.innerHTML =
      '<div id="view-actions"><button id="bp-save-btn"></button><button id="bp-discard-btn"></button></div>';
    document.body.appendChild(root);
  });

  it("defaults unlisted fields to optional when no rule exists", () => {
    Store.set({
      schemas: { W2: [{ name: "ssn", type: "string" }] },
      activeDocType: "W2",
      tenantId: "test-tenant",
      rules: {},
      ruleExists: false,
    });
    ExtractionRuleEditor.mount(root);
    const optionalRadio = root.querySelector('input[value="optional"]');
    expect(optionalRadio.checked).toBe(true);
  });

  it("defaults unlisted fields to excluded when a rule exists", () => {
    Store.set({
      schemas: {
        W2: [
          { name: "ssn", type: "string" },
          { name: "wages", type: "number" },
        ],
      },
      activeDocType: "W2",
      tenantId: "test-tenant",
      rules: { ssn: "required" },
      ruleExists: true,
    });
    ExtractionRuleEditor.mount(root);
    // wages is not in rules, so it should default to excluded
    const wagesRow = [...root.querySelectorAll(".field-row")][1];
    const excludedRadio = wagesRow.querySelector('input[value="excluded"]');
    expect(excludedRadio.checked).toBe(true);
  });
});
