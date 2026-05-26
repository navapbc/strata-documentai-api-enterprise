import { describe, it, expect, beforeEach, vi } from "vitest";

describe("schemas service", () => {
  let mockRequest, SchemasService;

  beforeEach(async () => {
    vi.resetModules();
    mockRequest = vi.fn().mockResolvedValue({});
    vi.doMock("../../src/services/http.js", () => ({
      adminClient: { request: mockRequest, configure: vi.fn(), getBaseUrl: () => "" },
      dataClient: { request: mockRequest, configure: vi.fn(), getBaseUrl: () => "" },
    }));
    SchemasService = await import("../../src/services/schemas.js");
  });

  it("list calls GET /v1/dictionary/schemas", async () => {
    mockRequest.mockResolvedValue({ schemas: ["W2", "I9"] });
    const result = await SchemasService.list();
    expect(mockRequest).toHaveBeenCalledWith("GET", "/v1/dictionary/schemas");
    expect(result).toEqual({ schemas: ["W2", "I9"] });
  });

  it("get calls GET with encoded documentType", async () => {
    mockRequest.mockResolvedValue({ fields: [{ name: "ssn" }] });
    const result = await SchemasService.get("W-2 Form");
    expect(mockRequest).toHaveBeenCalledWith("GET", "/v1/dictionary/schemas/W-2%20Form");
    expect(result.fields).toHaveLength(1);
  });

  it("getAllFields calls GET /v1/dictionary/fields", async () => {
    mockRequest.mockResolvedValue({ fields: [{ name: "ssn" }] });
    const result = await SchemasService.getAllFields();
    expect(mockRequest).toHaveBeenCalledWith("GET", "/v1/dictionary/fields");
    expect(result.fields).toHaveLength(1);
  });

  it("getCategories calls GET /v1/dictionary/document-categories", async () => {
    await SchemasService.getCategories();
    expect(mockRequest).toHaveBeenCalledWith("GET", "/v1/dictionary/document-categories");
  });
});
