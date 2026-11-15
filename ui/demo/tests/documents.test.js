import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock session storage key and adminClient before importing documents.js
vi.mock("../../shared/utils/session.js", () => ({
  STORAGE_KEY: "session",
}));

vi.mock("../../shared/services/http.js", () => ({
  adminClient: {
    getBaseUrl: () => "https://api.example.com",
  },
}));

import * as Documents from "../src/services/documents.js";

const PRESIGN_URL = "https://api.example.com/v1/demo/documents/presigned-url";
const S3_URL = "https://test-bucket.s3.amazonaws.com/";
const DIRECT_URL = "https://api.example.com/v1/demo/documents";

const PRESIGN_RESPONSE = {
  uploadUrl: S3_URL,
  fields: { key: "demo/tenant/file.pdf", "Content-Type": "application/pdf" },
  jobId: "job-abc-123",
};

function makeFile(name, type, size = 100) {
  const file = new File(["x".repeat(size)], name, { type });
  return file;
}

function mockSession(token = "test-token") {
  sessionStorage.setItem("session", JSON.stringify({ idToken: token }));
}

beforeEach(() => {
  sessionStorage.clear();
  mockSession();
  vi.restoreAllMocks();
});

describe("upload() — presigned path", () => {
  it("calls presign endpoint then POSTs to S3 and returns { jobId }", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, json: async () => PRESIGN_RESPONSE }) // presign
      .mockResolvedValueOnce({ ok: true }); // S3

    const file = makeFile("doc.pdf", "application/pdf");
    const result = await Documents.upload(file);

    expect(result).toEqual({ jobId: "job-abc-123" });

    // First call: presign
    const [presignCall] = fetchMock.mock.calls;
    expect(presignCall[0]).toBe(PRESIGN_URL);
    expect(presignCall[1].method).toBe("POST");

    // Second call: S3
    const [s3Call] = fetchMock.mock.calls.slice(1);
    expect(s3Call[0]).toBe(S3_URL);
    expect(s3Call[1].method).toBe("POST");

    // S3 form includes all presigned fields and the file
    const s3Body = s3Call[1].body;
    expect(s3Body.get("key")).toBe("demo/tenant/file.pdf");
    expect(s3Body.get("Content-Type")).toBe("application/pdf");
    expect(s3Body.get("file")).toBe(file);
  });

  it("sends Authorization header to presign endpoint", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, json: async () => PRESIGN_RESPONSE })
      .mockResolvedValueOnce({ ok: true });

    await Documents.upload(makeFile("doc.pdf", "application/pdf"));

    const [, opts] = fetchMock.mock.calls[0];
    expect(opts.headers.Authorization).toBe("Bearer test-token");
  });

  it("throws before calling presign when file exceeds max size", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const MAX = 524_288_000;
    const file = makeFile("big.pdf", "application/pdf", 1);
    Object.defineProperty(file, "size", { value: MAX + 1 });

    await expect(Documents.upload(file)).rejects.toThrow(/too large/i);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("surfaces the server detail on a presign 400", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 400,
      statusText: "Bad Request",
      json: async () => ({ detail: "Unsupported content type" }),
    });

    await expect(Documents.upload(makeFile("doc.pdf", "application/pdf"))).rejects.toThrow(
      "Unsupported content type",
    );
  });

  it("throws with storage error message on S3 failure", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, json: async () => PRESIGN_RESPONSE })
      .mockResolvedValueOnce({ ok: false, status: 403 });

    await expect(Documents.upload(makeFile("doc.pdf", "application/pdf"))).rejects.toThrow(
      "Upload to storage failed (403)",
    );
  });
});

describe("upload() — direct fallback path", () => {
  it("uses direct endpoint for a non-native type (image/heic)", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => ({ jobId: "job-direct-1" }),
    });

    const result = await Documents.upload(makeFile("photo.heic", "image/heic"));

    expect(result).toEqual({ jobId: "job-direct-1" });
    expect(fetchMock.mock.calls[0][0]).toBe(DIRECT_URL);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("uses direct endpoint when file.type is empty", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => ({ jobId: "job-direct-2" }),
    });

    const result = await Documents.upload(makeFile("unknown.bin", ""));

    expect(result).toEqual({ jobId: "job-direct-2" });
    expect(fetchMock.mock.calls[0][0]).toBe(DIRECT_URL);
  });

  it("surfaces server detail on direct upload failure", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 400,
      statusText: "Bad Request",
      json: async () => ({ detail: "File type not supported" }),
    });

    await expect(Documents.upload(makeFile("photo.heic", "image/heic"))).rejects.toThrow(
      "File type not supported",
    );
  });
});
