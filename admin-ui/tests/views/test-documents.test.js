import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

let TestDocumentsView, mockRun, mockGetTenantId, mockToast;

function flush() {
  return new Promise((r) => setTimeout(r, 0));
}

/**
 * jsdom has no DataTransfer and rejects assigning a plain array to input.files,
 * so the view's setFile() can't run unaided. Stub DataTransfer and make the
 * specific input's `files` property writable to simulate a real selection.
 */
function selectFile(root, file) {
  const input = root.querySelector("#test-file-input");
  Object.defineProperty(input, "files", { writable: true, configurable: true, value: [file] });
  input.dispatchEvent(new Event("change"));
}

describe("test-documents view", () => {
  let root;

  beforeEach(async () => {
    vi.resetModules();

    // Polyfill DataTransfer (absent in jsdom) - setFile() constructs one.
    vi.stubGlobal(
      "DataTransfer",
      class {
        constructor() {
          this._files = [];
          this.items = { add: (f) => this._files.push(f) };
        }
        get files() {
          return this._files;
        }
      },
    );

    mockRun = vi
      .fn()
      .mockResolvedValue({ status: "COMPLETED", matchedBlueprint: "W2", fields: {} });
    mockGetTenantId = vi.fn(() => "acme");
    mockToast = { show: vi.fn() };

    vi.doMock("../../src/services/blueprint-test.js", () => ({ run: mockRun }));
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

    TestDocumentsView = await import("../../src/views/test-documents/test-documents.js");
    root = document.createElement("div");
    document.body.appendChild(root);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    vi.unstubAllGlobals();
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

  it("run button is disabled until a file is selected", () => {
    TestDocumentsView.mount(root);
    expect(root.querySelector("#test-run-btn").disabled).toBe(true);
  });

  it("run button stays disabled when no tenant is selected even with a file", () => {
    mockGetTenantId.mockReturnValue(null);
    TestDocumentsView.mount(root);
    selectFile(root, new File(["x"], "doc.pdf"));
    expect(root.querySelector("#test-run-btn").disabled).toBe(true);
  });

  it("selecting a file shows the filename and enables run", () => {
    TestDocumentsView.mount(root);
    selectFile(root, new File(["x"], "doc.pdf"));
    expect(root.querySelector("#test-file-name").textContent).toBe("doc.pdf");
    expect(root.querySelector("#test-dropzone-idle").classList.contains("hidden")).toBe(true);
    expect(root.querySelector("#test-dropzone-selected").classList.contains("hidden")).toBe(false);
    expect(root.querySelector("#test-run-btn").disabled).toBe(false);
  });

  it("clicking the dropzone opens the file picker", () => {
    TestDocumentsView.mount(root);
    const input = root.querySelector("#test-file-input");
    const clickSpy = vi.spyOn(input, "click").mockImplementation(() => {});
    root.querySelector("#test-dropzone").click();
    expect(clickSpy).toHaveBeenCalled();
  });

  it("clear button resets the dropzone and does not open the picker", () => {
    TestDocumentsView.mount(root);
    selectFile(root, new File(["x"], "doc.pdf"));

    const input = root.querySelector("#test-file-input");
    const clickSpy = vi.spyOn(input, "click").mockImplementation(() => {});
    root.querySelector("#test-file-clear").click();

    expect(clickSpy).not.toHaveBeenCalled(); // stopPropagation kept dropzone from opening picker
    expect(root.querySelector("#test-dropzone-idle").classList.contains("hidden")).toBe(false);
    expect(root.querySelector("#test-dropzone-selected").classList.contains("hidden")).toBe(true);
    // Note: the run button re-disables via input.value="" clearing files, which is real
    // browser behaviour jsdom can't simulate - covered by the "disabled until file" test.
  });

  it("dragover adds the drag-over class and dragleave removes it", () => {
    TestDocumentsView.mount(root);
    const dz = root.querySelector("#test-dropzone");
    dz.dispatchEvent(new Event("dragover"));
    expect(dz.classList.contains("drag-over")).toBe(true);
    dz.dispatchEvent(new Event("dragleave"));
    expect(dz.classList.contains("drag-over")).toBe(false);
  });

  it("dropping a file selects it and clears the drag-over state", () => {
    TestDocumentsView.mount(root);
    const dz = root.querySelector("#test-dropzone");
    const input = root.querySelector("#test-file-input");
    Object.defineProperty(input, "files", { writable: true, configurable: true, value: [] });

    const dropEvent = new Event("drop");
    dropEvent.dataTransfer = { files: [new File(["x"], "dropped.pdf")] };
    dz.dispatchEvent(dropEvent);

    expect(dz.classList.contains("drag-over")).toBe(false);
    expect(root.querySelector("#test-file-name").textContent).toBe("dropped.pdf");
    expect(root.querySelector("#test-run-btn").disabled).toBe(false);
  });

  it("running a test calls the service without a category and renders results", async () => {
    mockRun.mockResolvedValue({
      status: "COMPLETED",
      matchedBlueprint: "W2",
      fields: { wages: { value: "50000", confidence: 0.95 } },
    });
    TestDocumentsView.mount(root);
    const file = new File(["x"], "doc.pdf");
    selectFile(root, file);

    root.querySelector("#test-run-btn").click();
    await flush();

    expect(mockRun).toHaveBeenCalledWith(file, "acme", null, null, expect.anything());
    const results = root.querySelector("#test-results");
    expect(results.classList.contains("hidden")).toBe(false);
    expect(results.textContent).toContain("W2");
    expect(results.textContent).toContain("wages");
  });

  it("shows a toast when the test fails", async () => {
    mockRun.mockRejectedValue(new Error("boom"));
    TestDocumentsView.mount(root);
    selectFile(root, new File(["x"], "doc.pdf"));

    root.querySelector("#test-run-btn").click();
    await flush();

    expect(mockToast.show).toHaveBeenCalledWith("Test failed: boom");
  });
});
