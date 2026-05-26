import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

let TestDocumentsView, mockRun, mockCategoriesList;

describe("test-documents view", () => {
  let root;

  beforeEach(async () => {
    vi.resetModules();

    mockRun = vi
      .fn()
      .mockResolvedValue({ status: "COMPLETED", matchedBlueprint: "W2", fields: {} });
    mockCategoriesList = vi
      .fn()
      .mockResolvedValue({ categories: [{ categoryName: "tax", displayName: "Tax" }] });

    vi.doMock("../../src/services/blueprint-test.js", () => ({ run: mockRun }));
    vi.doMock("../../src/services/document-categories.js", () => ({ list: mockCategoriesList }));
    vi.doMock("../../src/utils/tenant-context.js", () => ({
      getTenantId: vi.fn(() => "acme"),
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

    TestDocumentsView = await import("../../src/views/test-documents/test-documents.js");
    root = document.createElement("div");
    document.body.appendChild(root);

    // Mock global tenant select for populateTenantSelect
    const globalSelect = document.createElement("select");
    globalSelect.id = "global-tenant-select";
    const opt = document.createElement("option");
    opt.value = "acme";
    opt.textContent = "Acme";
    globalSelect.appendChild(opt);
    document.body.appendChild(globalSelect);
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("mounts with results and history containers", () => {
    TestDocumentsView.mount(root);
    expect(root.querySelector("#test-results")).toBeTruthy();
    expect(root.querySelector("#test-history-list")).toBeTruthy();
  });

  it("unmount clears root", () => {
    TestDocumentsView.mount(root);
    TestDocumentsView.unmount(root);
    expect(root.children.length).toBe(0);
  });
});
