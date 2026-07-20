import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { buildField, buildTenant } from "../factories.js";

let ExtractionRulesView, Store, mockGetAllFields;

const field = buildField();
const { tenantId: TENANT_ID } = buildTenant();

describe("extraction-rules view", () => {
  let root;

  beforeEach(async () => {
    vi.resetModules();

    mockGetAllFields = vi.fn().mockResolvedValue({ fields: [field] });

    vi.doMock("../../src/services/schemas.js", async () => ({
      ...(await vi.importActual("../../src/services/schemas.js")),
      getAllFields: mockGetAllFields,
    }));
    vi.doMock("../../src/services/rules.js", () => ({
      get: vi.fn().mockResolvedValue({ rules: [] }),
      put: vi.fn().mockResolvedValue({}),
    }));
    vi.doMock("../../src/utils/tenant-context.js", () => ({
      getTenantId: vi.fn(() => TENANT_ID),
      onChange: vi.fn(() => () => {}),
    }));
    vi.doMock("../../src/utils/helpers.js", () => ({
      esc: (s) => s,
      formatDate: (d) => d || "-",
      showLoading: vi.fn(),
      setViewActions: vi.fn(),
      clearViewActions: vi.fn(),
    }));
    vi.doMock("../../src/utils/toast.js", () => ({ show: vi.fn() }));

    Store = await import("../../src/state/blueprint-store.js");
    ExtractionRulesView = await import("../../src/views/extraction-rules/extraction-rules.js");
    root = document.createElement("div");
    document.body.appendChild(root);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    Store.reset();
  });

  it("mounts and loads schemas", async () => {
    ExtractionRulesView.mount(root);
    await new Promise((r) => setTimeout(r, 0));
    expect(mockGetAllFields).toHaveBeenCalled();
  });

  it("populates store with schemas grouped by docType", async () => {
    ExtractionRulesView.mount(root);
    await new Promise((r) => setTimeout(r, 0));
    const state = Store.get();
    expect(state.schemas[field.documentType]).toEqual([field]);
  });

  it("skips fetch when schemas are already preloaded", async () => {
    Store.set({ schemas: { [field.documentType]: [field] } });
    ExtractionRulesView.mount(root);
    await new Promise((r) => setTimeout(r, 0));
    expect(mockGetAllFields).not.toHaveBeenCalled();
  });

  it("unmount resets store and clears root", () => {
    ExtractionRulesView.mount(root);
    Store.set({ dirty: true, activeDocType: field.documentType });
    ExtractionRulesView.unmount(root);
    expect(Store.get().dirty).toBe(false);
    expect(Store.get().activeDocType).toBe(null);
    expect(root.children.length).toBe(0);
  });

  it("hasUnsavedChanges reflects store dirty state", () => {
    ExtractionRulesView.mount(root);
    expect(ExtractionRulesView.hasUnsavedChanges()).toBe(false);
    Store.set({ dirty: true });
    expect(ExtractionRulesView.hasUnsavedChanges()).toBe(true);
  });

  it("select sets activeDocType in store", () => {
    ExtractionRulesView.mount(root);
    ExtractionRulesView.select("I9");
    expect(Store.get().activeDocType).toBe("I9");
  });
});
