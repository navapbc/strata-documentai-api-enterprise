import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

describe("extraction-test service", () => {
  let ExtractionTestRunnerService;
  let fetchMock;

  beforeEach(async () => {
    vi.resetModules();
    vi.useFakeTimers();

    vi.doMock("../../src/services/http.js", () => ({
      adminClient: {
        request: vi.fn(),
        configure: vi.fn(),
        getBaseUrl: () => "http://localhost:8000",
      },
      dataClient: { request: vi.fn(), configure: vi.fn(), getBaseUrl: () => "" },
    }));

    const store = { docai_console_session: JSON.stringify({ idToken: "tok-123" }) };
    vi.stubGlobal("sessionStorage", {
      getItem: (k) => store[k] || null,
      setItem: (k, v) => {
        store[k] = v;
      },
    });

    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    ExtractionTestRunnerService = await import("../../src/services/extraction-test-runner.js");
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("posts FormData and polls until success", async () => {
    fetchMock
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ jobId: "j-1" }) })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ jobStatus: "success", isCompleted: true, extractedData: {} }),
      });

    const file = new File(["pdf"], "test.pdf", { type: "application/pdf" });
    const promise = ExtractionTestRunnerService.run(file, "acme", null);

    await vi.advanceTimersByTimeAsync(3000);
    const result = await promise;

    expect(result.jobStatus).toBe("success");
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8000/v1/admin/extraction-test");
    expect(fetchMock.mock.calls[0][1].method).toBe("POST");
    expect(fetchMock.mock.calls[1][0]).toContain("include_extracted_data=true");
  });

  it("throws on failed status", async () => {
    fetchMock
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ jobId: "j-2" }) })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            jobStatus: "failed",
            isCompleted: true,
            isFailed: true,
            message: "bad doc",
          }),
      });

    const file = new File(["pdf"], "test.pdf");
    const promise = ExtractionTestRunnerService.run(file, "acme", null);

    const caught = promise.catch((e) => e);
    await vi.advanceTimersByTimeAsync(3000);
    const err = await caught;
    expect(err).toBeInstanceOf(Error);
    expect(err.message).toBe("bad doc");
  });

  it("resolves on terminal non-success statuses", async () => {
    fetchMock
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ jobId: "j-3" }) })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({ jobStatus: "no_custom_blueprint_matched", isCompleted: true }),
      });

    const file = new File(["pdf"], "test.pdf");
    const promise = ExtractionTestRunnerService.run(file, "acme", null);

    await vi.advanceTimersByTimeAsync(3000);
    const result = await promise;
    expect(result.jobStatus).toBe("no_custom_blueprint_matched");
  });

  it("throws on non-ok start response", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      statusText: "Bad Request",
      json: () => Promise.resolve({ detail: "Invalid file" }),
    });

    const file = new File(["pdf"], "test.pdf");
    await expect(ExtractionTestRunnerService.run(file, "acme", null)).rejects.toThrow("Invalid file");
  });

  it("includes auth header from session", async () => {
    fetchMock
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ jobId: "j-4" }) })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ jobStatus: "success", isCompleted: true, extractedData: {} }),
      });

    const file = new File(["pdf"], "test.pdf");
    const promise = ExtractionTestRunnerService.run(file, "acme", null);
    await vi.advanceTimersByTimeAsync(3000);
    await promise;

    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe("Bearer tok-123");
  });
});
