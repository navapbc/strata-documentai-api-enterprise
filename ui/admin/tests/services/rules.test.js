import { describe, it, expect, beforeEach, vi } from "vitest";

describe("rules service", () => {
  let mockRequest, RulesService;

  beforeEach(async () => {
    vi.resetModules();
    mockRequest = vi.fn().mockResolvedValue({});
    vi.doMock("../../src/services/http.js", () => ({
      adminClient: { request: mockRequest, configure: vi.fn(), getBaseUrl: () => "" },
      dataClient: { request: mockRequest, configure: vi.fn(), getBaseUrl: () => "" },
    }));
    RulesService = await import("../../src/services/rules.js");
  });

  it("list calls GET with tenant_id", async () => {
    mockRequest.mockResolvedValue({ rules: [{ requiredFields: ["ssn"] }] });
    const result = await RulesService.list("acme");
    expect(mockRequest).toHaveBeenCalledWith("GET", "/v1/config/extraction-rules?tenant_id=acme");
    expect(result).toEqual({ rules: [{ requiredFields: ["ssn"] }] });
  });

  it("list without tenant_id omits param", async () => {
    mockRequest.mockResolvedValue({ rules: [] });
    const result = await RulesService.list(null);
    expect(mockRequest).toHaveBeenCalledWith("GET", "/v1/config/extraction-rules");
    expect(result).toEqual({ rules: [] });
  });

  it("put calls PUT with body", async () => {
    mockRequest.mockResolvedValue({ ok: true });
    const result = await RulesService.put("acme", "W2", ["ssn"], ["name"]);
    expect(mockRequest).toHaveBeenCalledWith("PUT", "/v1/config/extraction-rules", {
      tenant_id: "acme",
      document_type: "W2",
      required_fields: ["ssn"],
      optional_fields: ["name"],
    });
    expect(result).toEqual({ ok: true });
  });

  it("put includes blueprint_arn when provided", async () => {
    await RulesService.put("acme", "W2", [], [], "arn:aws:bda:123");
    expect(mockRequest).toHaveBeenCalledWith("PUT", "/v1/config/extraction-rules", {
      tenant_id: "acme",
      document_type: "W2",
      required_fields: [],
      optional_fields: [],
      blueprint_arn: "arn:aws:bda:123",
    });
  });

  it("get calls GET with tenant_id and document_type", async () => {
    mockRequest.mockResolvedValue({ rules: [{ requiredFields: ["name"] }] });
    const result = await RulesService.get("acme", "W2");
    expect(mockRequest).toHaveBeenCalledWith(
      "GET",
      "/v1/config/extraction-rules?tenant_id=acme&document_type=W2",
    );
    expect(result.rules[0].requiredFields).toEqual(["name"]);
  });

  it("remove calls DELETE with params", async () => {
    await RulesService.remove("acme", "W2");
    expect(mockRequest).toHaveBeenCalledWith(
      "DELETE",
      "/v1/config/extraction-rules?tenant_id=acme&document_type=W2",
    );
  });
});
