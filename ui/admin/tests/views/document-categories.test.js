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
      getOptions: vi.fn(() => []),
      mountSelect: vi.fn(),
      unmountSelect: vi.fn(),
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
        {
          tenantId: "acme",
          categoryName: "tax",
          displayName: "Tax Forms",
          isActive: true,
          processingPercentage: 0.5,
        },
      ],
    });
    DocCategoriesView.mount(root);
    await new Promise((r) => setTimeout(r, 0));
    expect(root.querySelectorAll("#categories-tbody tr").length).toBe(1);
    expect(root.querySelector("#categories-tbody").textContent).toContain("50%");
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

  it("renders System badge for auto-registered category", async () => {
    mockList.mockResolvedValue({
      categories: [
        {
          tenantId: "acme",
          categoryName: "tax",
          displayName: "Tax Forms",
          isActive: true,
          isAutoRegistered: true,
        },
      ],
    });
    DocCategoriesView.mount(root);
    await new Promise((r) => setTimeout(r, 0));
    const badge = root.querySelector(".badge-info");
    expect(badge).not.toBeNull();
    expect(badge.textContent).toBe("System");
  });

  it("renders Manual badge for manually created category", async () => {
    mockList.mockResolvedValue({
      categories: [
        {
          tenantId: "acme",
          categoryName: "tax",
          displayName: "Tax Forms",
          isActive: true,
          isAutoRegistered: false,
        },
      ],
    });
    DocCategoriesView.mount(root);
    await new Promise((r) => setTimeout(r, 0));
    const badge = root.querySelector(".badge-warning");
    expect(badge).not.toBeNull();
    expect(badge.textContent).toBe("Manual");
  });

  it("hides dates section on create modal", async () => {
    DocCategoriesView.mount(root);
    await new Promise((r) => setTimeout(r, 0));
    root.querySelector("#category-modal");
    // Trigger create modal via the create button
    const createBtn = Array.from(document.querySelectorAll("button")).find(
      (b) => b.textContent === "Create Category",
    );
    createBtn?.click();
    expect(root.querySelector("#category-dates").classList.contains("hidden")).toBe(true);
  });

  it("shows dates in edit modal with formatted values", async () => {
    mockList.mockResolvedValue({
      categories: [
        {
          tenantId: "acme",
          categoryName: "tax",
          displayName: "Tax Forms",
          isActive: true,
          createdAt: "2026-01-15T10:00:00.000Z",
          updatedAt: "2026-07-23T18:00:00.000Z",
        },
      ],
    });
    DocCategoriesView.mount(root);
    await new Promise((r) => setTimeout(r, 0));

    root.querySelector(".btn-icon").click();

    const datesEl = root.querySelector("#category-dates");
    expect(datesEl.classList.contains("hidden")).toBe(false);
    expect(root.querySelector("#category-created-at").textContent).not.toBe("");
    expect(root.querySelector("#category-updated-at").textContent).not.toBe("");
  });

  it("deactivate modal confirms and calls remove", async () => {
    mockList.mockResolvedValue({
      categories: [
        { tenantId: "acme", categoryName: "tax", displayName: "Tax Forms", isActive: true },
      ],
    });
    DocCategoriesView.mount(root);
    await new Promise((r) => setTimeout(r, 0));

    const deactivateBtn = root.querySelector(".btn-icon-danger");
    expect(deactivateBtn).not.toBeNull();
    deactivateBtn.click();

    const modal = root.querySelector("#category-deactivate-modal");
    expect(modal.classList.contains("hidden")).toBe(false);
    expect(root.querySelector("#deactivate-category-name").textContent).toBe("tax");

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

    root.querySelector(".btn-icon-danger").click();
    const modal = root.querySelector("#category-deactivate-modal");
    expect(modal.classList.contains("hidden")).toBe(false);

    root.querySelector("#category-deactivate-cancel").click();
    expect(modal.classList.contains("hidden")).toBe(true);
  });
});
