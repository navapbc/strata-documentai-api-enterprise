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
    expect(mockList).toHaveBeenCalledWith({ tenantId: TENANT_ID, limit: 50, cursor: undefined });
  });

  it("shows no-documents when tenant not selected", async () => {
    mockGetTenantId.mockReturnValue(null);
    DocumentsView.mount(root);
    await DocumentsView.load();
    expect(root.querySelector("#no-documents").classList.contains("hidden")).toBe(false);
  });

  it("renders document rows", async () => {
    mockList.mockResolvedValue({
      documents: [buildDocument()],
      nextCursor: null,
    });
    DocumentsView.mount(root);
    await flush();
    expect(root.querySelectorAll("#documents-tbody tr").length).toBe(1);
  });

  it("clicking a row loads document detail", async () => {
    const document = buildDocument();
    mockList.mockResolvedValue({
      documents: [document],
      nextCursor: null,
    });
    DocumentsView.mount(root);
    await flush();

    root.querySelector("#documents-tbody tr").click();
    await flush();

    expect(mockGet).toHaveBeenCalledWith(document.jobId);
    const detail = root.querySelector("#document-detail-panel");
    expect(detail.textContent).toContain("test.pdf");
  });

  it("next button enabled when nextCursor present", async () => {
    mockList.mockResolvedValue({ documents: [buildDocument()], nextCursor: "cur1" });
    DocumentsView.mount(root);
    await flush();
    expect(root.querySelector("#documents-next-btn").disabled).toBe(false);
  });

  it("next button disabled when no nextCursor", async () => {
    mockList.mockResolvedValue({ documents: [buildDocument()], nextCursor: null });
    DocumentsView.mount(root);
    await flush();
    expect(root.querySelector("#documents-next-btn").disabled).toBe(true);
  });

  it("clicking next loads next page", async () => {
    mockList.mockResolvedValue({ documents: [buildDocument()], nextCursor: "page2" });
    DocumentsView.mount(root);
    await flush();

    mockList.mockResolvedValue({ documents: [buildDocument()], nextCursor: null });
    root.querySelector("#documents-next-btn").click();
    await flush();

    expect(mockList).toHaveBeenLastCalledWith({ tenantId: TENANT_ID, limit: 50, cursor: "page2" });
  });

  it("clicking prev goes back", async () => {
    mockList.mockResolvedValue({ documents: [buildDocument()], nextCursor: "page2" });
    DocumentsView.mount(root);
    await flush();

    mockList.mockResolvedValue({ documents: [buildDocument()], nextCursor: null });
    root.querySelector("#documents-next-btn").click();
    await flush();

    root.querySelector("#documents-prev-btn").click();
    await flush();

    expect(mockList).toHaveBeenLastCalledWith({
      tenantId: TENANT_ID,
      limit: 50,
      cursor: undefined,
    });
  });

  it("unmount cleans up", () => {
    DocumentsView.mount(root);
    DocumentsView.unmount(root);
    expect(root.children.length).toBe(0);
  });
});
