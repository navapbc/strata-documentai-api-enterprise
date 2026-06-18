import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

let DocumentsView, mockGet, mockGetPreviewUrl, mockToast;

// Mirror the storage keys used by the documents view.
const STORAGE_KEY_ACTIVE = "docai_documents_active_job";
const STORAGE_KEY_SEARCHES = "docai_documents_searches";

function flush() {
  return new Promise((r) => setTimeout(r, 0));
}

function row(overrides = {}) {
  return {
    jobId: "j-1",
    fileName: "test.pdf",
    processStatus: "completed",
    createdAt: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function seedSearches(rows) {
  sessionStorage.setItem(STORAGE_KEY_SEARCHES, JSON.stringify(rows));
}

describe("documents view", () => {
  let root;

  async function search(jobId) {
    const input = root.querySelector("#document-search-input");
    input.value = jobId;
    input.dispatchEvent(new Event("input"));
    root.querySelector("#document-search-btn").click();
    await flush();
    await flush();
  }

  beforeEach(async () => {
    vi.resetModules();
    sessionStorage.clear();

    mockGet = vi.fn().mockResolvedValue({
      jobId: "j-1",
      fileName: "test.pdf",
      processStatus: "completed",
      contentType: "application/pdf",
      fields: { ssn: "123" },
    });
    mockGetPreviewUrl = vi.fn().mockResolvedValue({
      url: "https://s3.example.com/presigned",
      contentType: "application/pdf",
      expiresIn: 300,
    });
    mockToast = { show: vi.fn() };

    vi.doMock("../../src/services/documents.js", () => ({
      get: mockGet,
      getPreviewUrl: mockGetPreviewUrl,
    }));
    vi.doMock("../../src/utils/helpers.js", () => ({
      esc: (s) => s,
      formatDate: (d) => d || "-",
      showLoading: vi.fn(),
      setViewActions: vi.fn(),
      clearViewActions: vi.fn(),
    }));
    vi.doMock("../../src/utils/toast.js", () => mockToast);
    vi.doMock("../../src/utils/session.js", () => ({
      getEmail: () => "viewer@example.com",
    }));

    DocumentsView = await import("../../src/views/documents/documents.js");
    root = document.createElement("div");
    document.body.appendChild(root);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    sessionStorage.clear();
  });

  it("shows empty-state prompt and fetches nothing when there are no saved searches", async () => {
    DocumentsView.mount(root);
    await flush();

    const noDoc = root.querySelector("#no-documents");
    expect(noDoc.classList.contains("hidden")).toBe(false);
    expect(noDoc.textContent).toContain("Search for a document");
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("rebuilds the sidebar from cached searches without re-fetching each document", async () => {
    seedSearches([
      row({ jobId: "j-1", fileName: "first.pdf" }),
      row({ jobId: "j-2", fileName: "second.pdf" }),
    ]);

    DocumentsView.mount(root);
    await flush();

    expect(root.querySelectorAll("#documents-list .doc-list-item").length).toBe(2);
    expect(root.querySelector("#no-documents").classList.contains("hidden")).toBe(true);
    // Option 3: repopulating the list must not log a view/search audit event.
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("ignores the legacy bare-string cache format", async () => {
    sessionStorage.setItem(STORAGE_KEY_SEARCHES, JSON.stringify(["j-1", "j-2"]));

    DocumentsView.mount(root);
    await flush();

    expect(root.querySelectorAll("#documents-list .doc-list-item").length).toBe(0);
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("restores the active document on mount and fetches its detail", async () => {
    seedSearches([row({ jobId: "j-1", fileName: "first.pdf" })]);
    sessionStorage.setItem(STORAGE_KEY_ACTIVE, "j-1");

    DocumentsView.mount(root);
    await flush();
    await flush();

    expect(mockGet).toHaveBeenCalledWith("j-1");
    expect(root.querySelector("#detail-content").innerHTML).toContain("test.pdf");
  });

  it("clicking a cached list item loads document detail", async () => {
    seedSearches([row({ jobId: "j-1", fileName: "first.pdf" })]);
    DocumentsView.mount(root);
    await flush();

    root.querySelector(".doc-list-item").click();
    await flush();

    expect(mockGet).toHaveBeenCalledWith("j-1");
    expect(root.querySelector("#detail-content").innerHTML).toContain("test.pdf");
  });

  it("clicking a cached list item marks it active", async () => {
    seedSearches([
      row({ jobId: "j-1", fileName: "first.pdf" }),
      row({ jobId: "j-2", fileName: "second.pdf" }),
    ]);
    DocumentsView.mount(root);
    await flush();

    const items = root.querySelectorAll(".doc-list-item");
    items[1].click();
    await flush();

    expect(items[0].classList.contains("active")).toBe(false);
    expect(items[1].classList.contains("active")).toBe(true);
  });

  it("search button disabled when input empty", () => {
    DocumentsView.mount(root);
    expect(root.querySelector("#document-search-btn").disabled).toBe(true);
  });

  it("search button enabled when input has value", () => {
    DocumentsView.mount(root);
    const input = root.querySelector("#document-search-input");
    input.value = "abc";
    input.dispatchEvent(new Event("input"));
    expect(root.querySelector("#document-search-btn").disabled).toBe(false);
  });

  it("search calls get, renders detail, and caches the row", async () => {
    DocumentsView.mount(root);
    await flush();

    await search("j-1");

    expect(mockGet).toHaveBeenCalledWith("j-1");
    expect(root.querySelector("#detail-content").innerHTML).toContain("test.pdf");

    const cached = JSON.parse(sessionStorage.getItem(STORAGE_KEY_SEARCHES));
    expect(cached).toHaveLength(1);
    expect(cached[0].jobId).toBe("j-1");
    expect(sessionStorage.getItem(STORAGE_KEY_ACTIVE)).toBe("j-1");
  });

  it("search shows toast on 404", async () => {
    const err = new Error("Not found");
    err.status = 404;
    mockGet.mockRejectedValue(err);

    DocumentsView.mount(root);
    await flush();
    await search("missing");

    expect(mockToast.show).toHaveBeenCalledWith("Document not found");
  });

  it("unmount clears root", () => {
    DocumentsView.mount(root);
    DocumentsView.unmount(root);
    expect(root.children.length).toBe(0);
  });

  it("renders PDF preview with object tag", async () => {
    DocumentsView.mount(root);
    await flush();
    await search("j-1");

    const preview = root.querySelector("#document-preview-panel");
    expect(preview.querySelector("object")).not.toBeNull();
    expect(preview.innerHTML).toContain("application/pdf");
  });

  it("renders image preview with img tag", async () => {
    mockGet.mockResolvedValue({
      jobId: "j-img",
      fileName: "photo.jpg",
      processStatus: "completed",
      contentType: "image/jpeg",
    });
    mockGetPreviewUrl.mockResolvedValue({
      url: "https://s3.example.com/photo.jpg",
      contentType: "image/jpeg",
      expiresIn: 300,
    });
    DocumentsView.mount(root);
    await flush();
    await search("j-img");

    const preview = root.querySelector("#document-preview-panel");
    expect(preview.querySelector("img")).not.toBeNull();
    expect(preview.innerHTML).toContain("photo.jpg");
  });

  it("shows unavailable message when preview request fails", async () => {
    mockGetPreviewUrl.mockRejectedValue(new Error("failed"));
    DocumentsView.mount(root);
    await flush();
    await search("j-1");

    const preview = root.querySelector("#document-preview-panel");
    expect(preview.innerHTML).toContain("Preview unavailable");
  });
});
