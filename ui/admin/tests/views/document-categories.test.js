import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

let DocCategoriesView, mockList, mockCreate, mockRemove;

describe("document-categories view", () => {
  let root;

  beforeEach(async () => {
    vi.resetModules();

    mockList = vi.fn().mockResolvedValue({ categories: [] });
    mockCreate = vi.fn().mockResolvedValue({});
    mockRemove = vi.fn().mockResolvedValue({});

    vi.doMock("../../src/services/document-categories.js", () => ({
      list: mockList,
      create: mockCreate,
      update: vi.fn().mockResolvedValue({}),
      remove: mockRemove,
    }));
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
      bindSortHeaders: vi.fn(() => () => {}),
      sortRows: (rows) => rows,
    }));
    vi.doMock("../../src/utils/toast.js", () => ({ show: vi.fn() }));

    DocCategoriesView = await import("../../src/views/document-categories/document-categories.js");
    root = document.createElement("div");
    document.body.appendChild(root);
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("mounts and loads categories", async () => {
    DocCategoriesView.mount(root);
    await new Promise((r) => setTimeout(r, 0));
    expect(mockList).toHaveBeenCalled();
  });

  it("renders category rows", async () => {
    mockList.mockResolvedValue({
      categories: [
        { tenantId: "acme", categoryName: "tax", displayName: "Tax Forms", isActive: true },
      ],
    });
    DocCategoriesView.mount(root);
    await new Promise((r) => setTimeout(r, 0));
    expect(root.querySelectorAll("#categories-tbody tr").length).toBe(1);
  });

  it("shows empty state when no categories", async () => {
    DocCategoriesView.mount(root);
    await new Promise((r) => setTimeout(r, 0));
    expect(root.querySelector("#no-categories").classList.contains("hidden")).toBe(false);
  });

  it("unmount clears root", () => {
    DocCategoriesView.mount(root);
    DocCategoriesView.unmount(root);
    expect(root.children.length).toBe(0);
  });

  it("opens deactivate modal and confirms deactivation", async () => {
    mockList.mockResolvedValue({
      categories: [
        { tenantId: "acme", categoryName: "tax", displayName: "Tax Forms", isActive: true },
      ],
    });
    DocCategoriesView.mount(root);
    await new Promise((r) => setTimeout(r, 0));

    // Click deactivate button
    const deactivateBtn = root.querySelector(".btn-outline-danger");
    expect(deactivateBtn).not.toBeNull();
    deactivateBtn.click();

    // Modal should be visible
    const modal = root.querySelector("#category-deactivate-modal");
    expect(modal.classList.contains("hidden")).toBe(false);
    expect(root.querySelector("#deactivate-category-name").textContent).toBe("tax");

    // Confirm deactivation
    root.querySelector("#category-deactivate-confirm").click();
    await new Promise((r) => setTimeout(r, 0));

    expect(mockRemove).toHaveBeenCalledWith("acme", "tax");
  });

  it("closes deactivate modal on cancel", async () => {
    mockList.mockResolvedValue({
      categories: [
        { tenantId: "acme", categoryName: "tax", displayName: "Tax Forms", isActive: true },
      ],
    });
    DocCategoriesView.mount(root);
    await new Promise((r) => setTimeout(r, 0));

    root.querySelector(".btn-outline-danger").click();
    const modal = root.querySelector("#category-deactivate-modal");
    expect(modal.classList.contains("hidden")).toBe(false);

    root.querySelector("#category-deactivate-cancel").click();
    expect(modal.classList.contains("hidden")).toBe(true);
  });
});
