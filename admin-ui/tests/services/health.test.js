import { describe, it, expect, beforeEach, vi } from "vitest";

describe("health service", () => {
  let mockRequest, HealthService;

  beforeEach(async () => {
    vi.resetModules();
    mockRequest = vi.fn().mockResolvedValue({ status: "ok" });
    vi.doMock("../../src/services/http.js", () => ({
      adminClient: { request: mockRequest, configure: vi.fn(), getBaseUrl: () => "" },
      dataClient: { request: mockRequest, configure: vi.fn(), getBaseUrl: () => "" },
    }));
    HealthService = await import("../../src/services/health.js");
  });

  it("check calls GET /health on dataClient", async () => {
    const result = await HealthService.check();
    expect(mockRequest).toHaveBeenCalledWith("GET", "/health");
    expect(result).toEqual({ status: "ok" });
  });
});
