import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock shared modules
vi.mock("../../shared/utils/session.js", () => ({
  getEmail: () => "test@example.com",
  get: () => ({ idToken: "fake-token" }),
}));

vi.mock("../../shared/utils/toast.js", () => ({
  show: vi.fn(),
}));

vi.mock("../src/services/documents.js", () => ({
  upload: vi.fn(),
  list: vi.fn().mockResolvedValue({ documents: [] }),
  get: vi.fn(),
  getPreviewUrl: vi.fn(),
}));

import * as UploadView from "../src/views/upload/upload.js";
import * as Documents from "../src/services/documents.js";
import * as Toast from "../../shared/utils/toast.js";

describe("upload view", () => {
  let root;

  beforeEach(() => {
    root = document.createElement("div");
    document.body.appendChild(root);
    vi.useFakeTimers();
  });

  afterEach(() => {
    UploadView.unmount();
    document.body.removeChild(root);
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("mounts and renders the upload form", () => {
    UploadView.mount(root);
    expect(root.querySelector("#demo-dropzone")).toBeTruthy();
    expect(root.querySelector("#demo-run-btn")).toBeTruthy();
    expect(root.querySelector("#demo-run-btn").disabled).toBe(true);
  });

  it("displays user email in header", () => {
    UploadView.mount(root);
    expect(root.querySelector("#demo-user-email").textContent).toBe("test@example.com");
  });

  it("enables extract button when file is selected", () => {
    UploadView.mount(root);
    const input = root.querySelector("#demo-file-input");
    const file = new File(["content"], "test.pdf", { type: "application/pdf" });
    Object.defineProperty(input, "files", { value: [file], configurable: true });
    input.dispatchEvent(new Event("change"));

    expect(root.querySelector("#demo-run-btn").disabled).toBe(false);
    expect(root.querySelector("#demo-file-name").textContent).toBe("test.pdf");
  });

  it("disables extract button when file is cleared", () => {
    UploadView.mount(root);
    const input = root.querySelector("#demo-file-input");
    const file = new File(["content"], "test.pdf", { type: "application/pdf" });
    Object.defineProperty(input, "files", { value: [file], configurable: true });
    input.dispatchEvent(new Event("change"));

    root.querySelector("#demo-file-clear").click();
    expect(root.querySelector("#demo-run-btn").disabled).toBe(true);
  });

  it("calls Documents.upload on extract click", async () => {
    Documents.upload.mockResolvedValue({ jobId: "job-123" });
    Documents.get.mockResolvedValue({
      processStatus: "completed",
      fields: {},
      jobId: "job-123",
    });

    UploadView.mount(root);

    // Select file
    const input = root.querySelector("#demo-file-input");
    const file = new File(["content"], "test.pdf", { type: "application/pdf" });
    Object.defineProperty(input, "files", { value: [file], configurable: true });
    input.dispatchEvent(new Event("change"));

    // Click extract
    root.querySelector("#demo-run-btn").click();

    // Advance past poll interval
    await vi.advanceTimersByTimeAsync(3500);

    expect(Documents.upload).toHaveBeenCalledWith(file);
  });

  it("shows toast on upload failure", async () => {
    Documents.upload.mockRejectedValue(new Error("Network error"));

    UploadView.mount(root);

    const input = root.querySelector("#demo-file-input");
    const file = new File(["content"], "test.pdf", { type: "application/pdf" });
    Object.defineProperty(input, "files", { value: [file], configurable: true });
    input.dispatchEvent(new Event("change"));

    root.querySelector("#demo-run-btn").click();
    await vi.advanceTimersByTimeAsync(100);

    expect(Toast.show).toHaveBeenCalledWith("Extraction failed: Network error");
  });

  it("fires onLogout callback when sign out clicked", () => {
    const cb = vi.fn();
    UploadView.onLogout(cb);
    UploadView.mount(root);

    root.querySelector("#demo-logout-btn").click();
    expect(cb).toHaveBeenCalled();
  });
});
