import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { buildDocument } from "../factories.js";

let DocumentSearchView,
  mockSearch,
  mockGetTenantId,
  mockOnChange,
  mockListCategories,
  mockListSchemas;

function flush() {
  return new Promise((r) => setTimeout(r, 0));
}

describe("document-search view", () => {
  let root, tenantChangeCallback;

  beforeEach(async () => {
    vi.resetModules();
    tenantChangeCallback = null;

    mockSearch = vi.fn().mockResolvedValue({ documents: [], nextCursor: null });
    mockGetTenantId = vi.fn(() => null);
    mockOnChange = vi.fn((fn) => {
      tenantChangeCallback = fn;
      return () => {};
    });
    mockListCategories = vi.fn().mockResolvedValue({ categories: [] });
    mockListSchemas = vi.fn().mockResolvedValue({ schemas: ["invoice", "w2-form"] });

    vi.doMock("../../src/services/documents.js", () => ({ search: mockSearch }));
    vi.doMock("../../src/services/document-categories.js", () => ({ list: mockListCategories }));
    vi.doMock("../../src/services/schemas.js", () => ({ list: mockListSchemas }));
    vi.doMock("../../src/utils/tenant-context.js", () => ({
      getTenantId: mockGetTenantId,
      onChange: mockOnChange,
      mountSelect: vi.fn(),
      unmountSelect: vi.fn(),
    }));
    vi.doMock("../../src/utils/helpers.js", () => ({
      esc: (s) => s,
      formatDate: (d) => d || "-",
      setViewActions: vi.fn(),
    }));
    vi.doMock("../../src/utils/session.js", () => ({ getEmail: () => "admin@test.com" }));
    vi.doMock("../../src/utils/toast.js", () => ({ show: vi.fn() }));

    DocumentSearchView = await import("../../src/views/document-search/document-search.js");
    root = document.createElement("div");
    document.body.appendChild(root);
    DocumentSearchView.mount(root);
    await flush();
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  // --- mount ---

  it("loads blueprints on mount", () => {
    expect(mockListSchemas).toHaveBeenCalledOnce();
  });

  it("filter-main is hidden on mount", () => {
    expect(root.querySelector(".filter-main").style.display).toBe("none");
  });

  it("results tab is disabled on mount", () => {
    expect(root.querySelector(".sidebar-tab[data-tab='results']").disabled).toBe(true);
  });

  // --- tenant validation ---

  it("shows tenant error message when searching without a tenant", () => {
    root.querySelector("#doc-search-btn").click();
    expect(root.querySelector("#doc-search-tenant-msg").classList.contains("hidden")).toBe(false);
    expect(mockSearch).not.toHaveBeenCalled();
  });

  it("hides tenant error message on tenant change", () => {
    root.querySelector("#doc-search-btn").click();
    tenantChangeCallback();
    expect(root.querySelector("#doc-search-tenant-msg").classList.contains("hidden")).toBe(true);
  });

  // --- search ---

  it("calls search with tenantId when tenant is selected", async () => {
    mockGetTenantId.mockReturnValue("acme");
    root.querySelector("#doc-search-btn").click();
    await flush();
    expect(mockSearch).toHaveBeenCalledWith(expect.objectContaining({ tenantId: "acme" }));
  });

  it("shows no-documents message when search returns empty", async () => {
    mockGetTenantId.mockReturnValue("acme");
    root.querySelector("#doc-search-btn").click();
    await flush();
    const noDoc = root.querySelector("#no-documents");
    expect(noDoc.classList.contains("hidden")).toBe(false);
    expect(noDoc.textContent).toContain("No documents found");
  });

  it("renders results and enables results tab after search", async () => {
    mockGetTenantId.mockReturnValue("acme");
    mockSearch.mockResolvedValue({
      documents: [buildDocument(), buildDocument({ jobId: "j-2" })],
      nextCursor: null,
    });
    root.querySelector("#doc-search-btn").click();
    await flush();
    const resultsTab = root.querySelector(".sidebar-tab[data-tab='results']");
    expect(resultsTab.disabled).toBe(false);
    expect(resultsTab.textContent).toBe("Results (2)");
    expect(root.querySelectorAll(".doc-list-item").length).toBe(2);
  });

  it("switches to results tab after search", async () => {
    mockGetTenantId.mockReturnValue("acme");
    mockSearch.mockResolvedValue({ documents: [buildDocument()], nextCursor: null });
    root.querySelector("#doc-search-btn").click();
    await flush();
    expect(
      root.querySelector(".sidebar-tab[data-tab='results']").classList.contains("active"),
    ).toBe(true);
    expect(
      root.querySelector(".sidebar-tab[data-tab='filters']").classList.contains("active"),
    ).toBe(false);
  });

  it("shows filter-main when results tab is active", async () => {
    mockGetTenantId.mockReturnValue("acme");
    mockSearch.mockResolvedValue({ documents: [buildDocument()], nextCursor: null });
    root.querySelector("#doc-search-btn").click();
    await flush();
    expect(root.querySelector(".filter-main").style.display).toBe("");
  });

  it("passes filename filter to search", async () => {
    mockGetTenantId.mockReturnValue("acme");
    root.querySelector("#doc-search-filename").value = "invoice";
    root.querySelector("#doc-search-btn").click();
    await flush();
    expect(mockSearch).toHaveBeenCalledWith(expect.objectContaining({ filename: "invoice" }));
  });

  it("triggers search on Enter in filename input", async () => {
    mockGetTenantId.mockReturnValue("acme");
    const input = root.querySelector("#doc-search-filename");
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await flush();
    expect(mockSearch).toHaveBeenCalled();
  });

  // --- results tab label ---

  it("shows + suffix when nextCursor is present", async () => {
    mockGetTenantId.mockReturnValue("acme");
    mockSearch.mockResolvedValue({
      documents: Array.from({ length: 50 }, (_, i) => buildDocument({ jobId: `j-${i}` })),
      nextCursor: "abc123",
    });
    root.querySelector("#doc-search-btn").click();
    await flush();
    expect(root.querySelector(".sidebar-tab[data-tab='results']").textContent).toBe(
      "Results (50+)",
    );
  });

  it("does not show + suffix when nextCursor is null", async () => {
    mockGetTenantId.mockReturnValue("acme");
    mockSearch.mockResolvedValue({ documents: [buildDocument()], nextCursor: null });
    root.querySelector("#doc-search-btn").click();
    await flush();
    expect(root.querySelector(".sidebar-tab[data-tab='results']").textContent).toBe("Results (1)");
  });

  // --- load more ---

  it("load more button is hidden when no nextCursor", async () => {
    mockGetTenantId.mockReturnValue("acme");
    mockSearch.mockResolvedValue({ documents: [buildDocument()], nextCursor: null });
    root.querySelector("#doc-search-btn").click();
    await flush();
    expect(root.querySelector("#doc-search-load-more").classList.contains("hidden")).toBe(true);
  });

  it("load more button is visible when nextCursor present", async () => {
    mockGetTenantId.mockReturnValue("acme");
    mockSearch.mockResolvedValue({
      documents: Array.from({ length: 50 }, (_, i) => buildDocument({ jobId: `j-${i}` })),
      nextCursor: "abc123",
    });
    root.querySelector("#doc-search-btn").click();
    await flush();
    expect(root.querySelector("#doc-search-load-more").classList.contains("hidden")).toBe(false);
  });

  it("load more passes cursor and appends results", async () => {
    mockGetTenantId.mockReturnValue("acme");
    mockSearch.mockResolvedValueOnce({
      documents: Array.from({ length: 50 }, (_, i) => buildDocument({ jobId: `j-${i}` })),
      nextCursor: "page2",
    });
    root.querySelector("#doc-search-btn").click();
    await flush();

    mockSearch.mockResolvedValueOnce({
      documents: [buildDocument({ jobId: "j-50" })],
      nextCursor: null,
    });
    root.querySelector("#doc-search-load-more").click();
    await flush();

    expect(mockSearch).toHaveBeenLastCalledWith(expect.objectContaining({ cursor: "page2" }));
    expect(root.querySelector(".sidebar-tab[data-tab='results']").textContent).toBe("Results (51)");
    expect(root.querySelector("#doc-search-load-more").classList.contains("hidden")).toBe(true);
  });

  // --- clear ---

  it("clear resets inputs and results tab", async () => {
    mockGetTenantId.mockReturnValue("acme");
    mockSearch.mockResolvedValue({ documents: [buildDocument()], nextCursor: null });
    root.querySelector("#doc-search-btn").click();
    await flush();

    root.querySelector("#doc-search-filename").value = "test";
    root.querySelector("#doc-search-clear-btn").click();

    expect(root.querySelector("#doc-search-filename").value).toBe("");
    const resultsTab = root.querySelector(".sidebar-tab[data-tab='results']");
    expect(resultsTab.disabled).toBe(true);
    expect(resultsTab.textContent).toBe("Results");
  });

  it("clear hides filter-main", async () => {
    mockGetTenantId.mockReturnValue("acme");
    mockSearch.mockResolvedValue({ documents: [buildDocument()], nextCursor: null });
    root.querySelector("#doc-search-btn").click();
    await flush();

    root.querySelector("#doc-search-clear-btn").click();
    expect(root.querySelector(".filter-main").style.display).toBe("none");
  });

  // --- categories ---

  it("loads categories when tenant changes", async () => {
    mockGetTenantId.mockReturnValue("acme");
    mockListCategories.mockResolvedValue({
      categories: [{ categoryName: "expenses" }, { categoryName: "income" }],
    });
    tenantChangeCallback();
    await flush();
    expect(mockListCategories).toHaveBeenCalledWith("acme");
    const options = root.querySelectorAll("#doc-search-doc-type option");
    expect(options.length).toBe(3); // Any + 2
  });

  // --- unmount ---

  it("unmount clears root", () => {
    DocumentSearchView.unmount(root);
    expect(root.children.length).toBe(0);
  });
});
