import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { buildDocument, buildTenant } from "../factories.js";

let DocumentsView, mockList, mockGet, mockGetTenantId, mockToast;

const { tenantId: TENANT_ID } = buildTenant();

function flush() {
  return new Promise((r) => setTimeout(r, 0));
}

describe("documents view", () => {
  let root;

  beforeEach(async () => {
    vi.resetModules();

    mockList = vi.fn().mockResolvedValue({ documents: [], nextCursor: null });
    mockGet = vi.fn().mockResolvedValue({
      jobId: "j-1",
      fileName: "test.pdf",
      processStatus: "completed",
      fields: { ssn: "123" },
    });
    mockGetTenantId = vi.fn().mockReturnValue(TENANT_ID);
    mockToast = { show: vi.fn() };

    vi.doMock("../../src/services/documents.js", () => ({ list: mockList, get: mockGet }));
    vi.doMock("../../src/utils/tenant-context.js", () => ({
      getTenantId: mockGetTenantId,
      onChange: vi.fn(() => () => {}),
    }));
    vi.doMock("../../src/utils/helpers.js", () => ({
      esc: (s) => s,
      formatDate: (d) => d || "-",
      showLoading: vi.fn(),
      setViewActions: vi.fn(),
      clearViewActions: vi.fn(),
    }));
    vi.doMock("../../src/utils/toast.js", () => mockToast);

    DocumentsView = await import("../../src/views/documents/documents.js");
    root = document.createElement("div");
    document.body.appendChild(root);
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("mounts and loads documents", async () => {
    DocumentsView.mount(root);
    await flush();
    expect(mockList).toHaveBeenCalledWith({ tenantId: TENANT_ID, limit: 50 });
  });

  it("shows message when tenant not selected", async () => {
    mockGetTenantId.mockReturnValue(null);
    DocumentsView.mount(root);
    await flush();
    const noDoc = root.querySelector("#no-documents");
    expect(noDoc.classList.contains("hidden")).toBe(false);
    expect(noDoc.textContent).toContain("Select a tenant");
  });

  it("renders document list items", async () => {
    mockList.mockResolvedValue({
      documents: [buildDocument(), buildDocument({ jobId: "j-2", fileName: "second.pdf" })],
      nextCursor: null,
    });
    DocumentsView.mount(root);
    await flush();
    expect(root.querySelectorAll("#documents-list .doc-list-item").length).toBe(2);
    expect(root.querySelector("#no-documents").classList.contains("hidden")).toBe(true);
  });

  it("shows no-documents when list is empty", async () => {
    mockList.mockResolvedValue({ documents: [] });
    DocumentsView.mount(root);
    await flush();
    expect(root.querySelector("#no-documents").classList.contains("hidden")).toBe(false);
  });

  it("clicking a list item loads document detail", async () => {
    mockList.mockResolvedValue({
      documents: [buildDocument()],
    });
    DocumentsView.mount(root);
    await flush();

    root.querySelector(".doc-list-item").click();
    await flush();

    expect(mockGet).toHaveBeenCalledWith("test-job-id");
    const detail = root.querySelector("#document-detail-panel");
    expect(detail.innerHTML).toContain("test.pdf");
  });

  it("clicking a list item marks it active", async () => {
    mockList.mockResolvedValue({
      documents: [buildDocument(), buildDocument({ jobId: "j-2", fileName: "b.pdf" })],
    });
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

  it("search calls get and renders detail", async () => {
    DocumentsView.mount(root);
    await flush();

    const input = root.querySelector("#document-search-input");
    input.value = "j-1";
    input.dispatchEvent(new Event("input"));
    root.querySelector("#document-search-btn").click();
    await flush();

    expect(mockGet).toHaveBeenCalledWith("j-1");
    expect(root.querySelector("#document-detail-panel").innerHTML).toContain("test.pdf");
  });

  it("search shows toast on 404", async () => {
    const err = new Error("Not found");
    err.status = 404;
    mockGet.mockRejectedValue(err);

    DocumentsView.mount(root);
    await flush();

    const input = root.querySelector("#document-search-input");
    input.value = "missing";
    input.dispatchEvent(new Event("input"));
    root.querySelector("#document-search-btn").click();
    await flush();

    expect(mockToast.show).toHaveBeenCalledWith("Document not found");
  });

  it("unmount clears root", () => {
    DocumentsView.mount(root);
    DocumentsView.unmount(root);
    expect(root.children.length).toBe(0);
  });
});
