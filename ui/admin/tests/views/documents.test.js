import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

let DocumentsView, mockList, mockGet, mockGetPreviewUrl, mockGetTenantId, mockOnChange;

const STORAGE_KEY_ACTIVE = "docai_documents_active_job";

function flush() {
  return new Promise((r) => setTimeout(r, 0));
}

function doc(overrides = {}) {
  return {
    jobId: "j-1",
    fileName: "test.pdf",
    processStatus: "success",
    createdAt: "2026-01-01T00:00:00Z",
    contentType: "application/pdf",
    ...overrides,
  };
}

describe("documents view", () => {
  let root;
  let tenantChangeCallback;

  beforeEach(async () => {
    vi.resetModules();
    sessionStorage.clear();
    tenantChangeCallback = null;

    mockList = vi.fn().mockResolvedValue({ documents: [] });
    mockGet = vi.fn().mockResolvedValue({
      jobId: "j-1",
      fileName: "test.pdf",
      processStatus: "success",
      contentType: "application/pdf",
      fields: { ssn: { value: "123", confidence: 0.95 } },
    });
    mockGetPreviewUrl = vi.fn().mockResolvedValue({
      url: "https://s3.example.com/presigned",
      contentType: "application/pdf",
      expiresIn: 300,
    });
    mockGetTenantId = vi.fn(() => null);
    mockOnChange = vi.fn((fn) => {
      tenantChangeCallback = fn;
      return () => {};
    });

    vi.doMock("../../src/services/documents.js", () => ({
      list: mockList,
      get: mockGet,
      getPreviewUrl: mockGetPreviewUrl,
    }));
    vi.doMock("../../src/utils/tenant-context.js", () => ({
      getTenantId: mockGetTenantId,
      onChange: mockOnChange,
      load: vi.fn(),
    }));
    vi.doMock("../../src/utils/helpers.js", () => ({
      esc: (s) => s,
      formatDate: (d) => d || "-",
      showLoading: vi.fn(),
      setViewActions: vi.fn(),
      clearViewActions: vi.fn(),
    }));
    vi.doMock("../../src/utils/session.js", () => ({
      getEmail: () => "admin@test.com",
    }));

    DocumentsView = await import("../../src/views/documents/documents.js");
    root = document.createElement("div");
    document.body.appendChild(root);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    sessionStorage.clear();
  });

  it("mounts with status filter dropdown", () => {
    DocumentsView.mount(root);
    expect(root.querySelector("#document-status-filter")).not.toBeNull();
  });

  it("shows tenant prompt when no tenant selected", async () => {
    DocumentsView.mount(root);
    await flush();

    const noDoc = root.querySelector("#no-documents");
    expect(noDoc.classList.contains("hidden")).toBe(false);
    expect(noDoc.textContent).toContain("Select a tenant");
    expect(mockList).not.toHaveBeenCalled();
  });

  it("calls list with tenantId and renders rows on tenant select", async () => {
    mockGetTenantId.mockReturnValue("tenant-a");
    mockList.mockResolvedValue({
      documents: [
        doc({ jobId: "j-1", fileName: "first.pdf" }),
        doc({ jobId: "j-2", fileName: "second.pdf" }),
      ],
    });

    DocumentsView.mount(root);
    await flush();

    expect(mockList).toHaveBeenCalledWith(
      expect.objectContaining({ tenantId: "tenant-a", limit: 25 }),
    );
    expect(root.querySelectorAll(".doc-list-item").length).toBe(2);
    expect(root.querySelector("#no-documents").classList.contains("hidden")).toBe(true);
  });

  it("passes status to list when status filter changes", async () => {
    mockGetTenantId.mockReturnValue("tenant-a");
    mockList.mockResolvedValue({ documents: [doc()] });

    DocumentsView.mount(root);
    await flush();

    mockList.mockClear();
    const select = root.querySelector("#document-status-filter");
    select.value = "failed";
    select.dispatchEvent(new Event("change"));
    await flush();

    expect(mockList).toHaveBeenCalledWith(
      expect.objectContaining({ tenantId: "tenant-a", status: "failed", limit: 25 }),
    );
  });

  it("renders success badge for processStatus success", async () => {
    mockGetTenantId.mockReturnValue("tenant-a");
    mockList.mockResolvedValue({ documents: [doc({ processStatus: "success" })] });

    DocumentsView.mount(root);
    await flush();

    const badge = root.querySelector(".badge");
    expect(badge.classList.contains("badge-success")).toBe(true);
  });

  it("renders danger badge for processStatus failed", async () => {
    mockGetTenantId.mockReturnValue("tenant-a");
    mockList.mockResolvedValue({ documents: [doc({ processStatus: "failed" })] });

    DocumentsView.mount(root);
    await flush();

    const badge = root.querySelector(".badge");
    expect(badge.classList.contains("badge-danger")).toBe(true);
  });

  it("clicking a row fetches detail with extracted data and bounding box", async () => {
    mockGetTenantId.mockReturnValue("tenant-a");
    mockList.mockResolvedValue({ documents: [doc()] });

    DocumentsView.mount(root);
    await flush();

    root.querySelector(".doc-list-item").click();
    await flush();

    expect(mockGet).toHaveBeenCalledWith("j-1", {
      includeExtractedData: true,
      includeBoundingBox: true,
    });
    expect(root.querySelector("#detail-content").innerHTML).toContain("test.pdf");
  });

  it("clicking a row loads preview", async () => {
    mockGetTenantId.mockReturnValue("tenant-a");
    mockList.mockResolvedValue({ documents: [doc()] });

    DocumentsView.mount(root);
    await flush();

    root.querySelector(".doc-list-item").click();
    await flush();

    expect(mockGetPreviewUrl).toHaveBeenCalledWith("j-1");
    const preview = root.querySelector("#document-preview-panel");
    expect(preview.querySelector("object")).not.toBeNull();
  });

  it("tenant change clears active job and reloads", async () => {
    mockGetTenantId.mockReturnValue("tenant-a");
    mockList.mockResolvedValue({ documents: [doc()] });

    DocumentsView.mount(root);
    await flush();

    // Click a doc to activate it
    root.querySelector(".doc-list-item").click();
    await flush();
    expect(sessionStorage.getItem(STORAGE_KEY_ACTIVE)).toBe("j-1");

    // Simulate tenant change
    mockGetTenantId.mockReturnValue("tenant-b");
    mockList.mockResolvedValue({ documents: [] });
    tenantChangeCallback();
    await flush();

    expect(sessionStorage.getItem(STORAGE_KEY_ACTIVE)).toBeNull();
    expect(root.querySelector("#detail-content").innerHTML).toBe("");
    expect(root.querySelector("#document-preview-panel").innerHTML).toContain(
      "Select a document to preview",
    );
    expect(root.querySelector("#document-detail-panel").classList.contains("collapsed")).toBe(true);
  });

  it("unmount clears root and unsubscribes from tenant changes", () => {
    DocumentsView.mount(root);
    DocumentsView.unmount(root);
    expect(root.children.length).toBe(0);
  });

  it("shows unavailable message when preview request fails", async () => {
    mockGetTenantId.mockReturnValue("tenant-a");
    mockList.mockResolvedValue({ documents: [doc()] });
    mockGetPreviewUrl.mockRejectedValue(new Error("failed"));

    DocumentsView.mount(root);
    await flush();

    root.querySelector(".doc-list-item").click();
    await flush();

    const preview = root.querySelector("#document-preview-panel");
    expect(preview.innerHTML).toContain("Preview unavailable");
  });

  it("renders extracted data revealed without toggle", async () => {
    mockGetTenantId.mockReturnValue("tenant-a");
    mockList.mockResolvedValue({ documents: [doc()] });

    DocumentsView.mount(root);
    await flush();

    root.querySelector(".doc-list-item").click();
    await flush();

    // Should show values, no toggle checkbox
    expect(root.querySelector(".extracted-data-toggle")).toBeNull();
    expect(root.querySelector(".extracted-data-table")).not.toBeNull();
  });

  it("shows empty state when list request fails", async () => {
    mockGetTenantId.mockReturnValue("tenant-a");
    mockList.mockRejectedValue(new Error("network error"));

    DocumentsView.mount(root);
    await flush();

    expect(root.querySelectorAll(".doc-list-item").length).toBe(0);
    const noDoc = root.querySelector("#no-documents");
    expect(noDoc.classList.contains("hidden")).toBe(false);
    expect(noDoc.textContent).toContain("No documents found");
  });

  it("restores active document from session storage on mount", async () => {
    mockGetTenantId.mockReturnValue("tenant-a");
    mockList.mockResolvedValue({
      documents: [
        doc({ jobId: "j-1", fileName: "first.pdf" }),
        doc({ jobId: "j-2", fileName: "second.pdf" }),
      ],
    });
    sessionStorage.setItem(STORAGE_KEY_ACTIVE, "j-1");

    DocumentsView.mount(root);
    await flush(); // list fetch
    await flush(); // loadDetail from restored active job

    const activeItem = root.querySelector('[data-job-id="j-1"]');
    expect(activeItem.classList.contains("active")).toBe(true);
    expect(mockGet).toHaveBeenCalledWith("j-1", {
      includeExtractedData: true,
      includeBoundingBox: true,
    });
  });
});
