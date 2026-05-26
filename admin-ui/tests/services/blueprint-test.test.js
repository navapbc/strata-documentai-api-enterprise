import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

describe("blueprint-test service", () => {
  let BlueprintTestService;
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

    BlueprintTestService = await import("../../src/services/blueprint-test.js");
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("posts FormData and polls until COMPLETED", async () => {
    fetchMock
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ testId: "t-1" }) })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: "COMPLETED", fields: {} }),
      });

    const file = new File(["pdf"], "test.pdf", { type: "application/pdf" });
    const promise = BlueprintTestService.run(file, "acme", "tax", null, null);

    await vi.advanceTimersByTimeAsync(3000);
    const result = await promise;

    expect(result.status).toBe("COMPLETED");
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8000/v1/admin/blueprints/test");
    expect(fetchMock.mock.calls[0][1].method).toBe("POST");
  });

  it("throws on FAILED status", async () => {
    fetchMock
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ testId: "t-2" }) })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: "FAILED", error: "bad doc" }),
      });

    const file = new File(["pdf"], "test.pdf");
    const promise = BlueprintTestService.run(file, "acme", "tax", null, null);

    // Attach catch immediately to prevent unhandled rejection
    const caught = promise.catch((e) => e);
    await vi.advanceTimersByTimeAsync(3000);
    const err = await caught;
    expect(err).toBeInstanceOf(Error);
    expect(err.message).toBe("bad doc");
  });

  it("throws on non-ok start response", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      statusText: "Bad Request",
      json: () => Promise.resolve({ detail: "Invalid file" }),
    });

    const file = new File(["pdf"], "test.pdf");
    await expect(BlueprintTestService.run(file, "acme", "tax", null, null)).rejects.toThrow(
      "Invalid file",
    );
  });

  it("includes auth header from session", async () => {
    fetchMock
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ testId: "t-4" }) })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: "COMPLETED", fields: {} }),
      });

    const file = new File(["pdf"], "test.pdf");
    const promise = BlueprintTestService.run(file, "acme", "tax", null, null);
    await vi.advanceTimersByTimeAsync(3000);
    await promise;

    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe("Bearer tok-123");
  });
});
