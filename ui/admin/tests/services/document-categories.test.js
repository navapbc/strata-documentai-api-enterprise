import { describe, it, expect, beforeEach, vi } from "vitest";

describe("document-categories service", () => {
  let mockRequest, CategoriesService;

  beforeEach(async () => {
    vi.resetModules();
    mockRequest = vi.fn().mockResolvedValue({});
    vi.doMock("../../src/services/http.js", () => ({
      adminClient: { request: mockRequest, configure: vi.fn(), getBaseUrl: () => "" },
      dataClient: { request: mockRequest, configure: vi.fn(), getBaseUrl: () => "" },
    }));
    CategoriesService = await import("../../src/services/document-categories.js");
  });

  it("list with tenantId and activeOnly", async () => {
    mockRequest.mockResolvedValue({ categories: [{ categoryName: "tax" }] });
    const result = await CategoriesService.list("acme", true);
    expect(mockRequest).toHaveBeenCalledWith("GET", "/v1/admin/document-categories?tenant_id=acme");
    expect(result.categories).toHaveLength(1);
  });

  it("list with activeOnly=false includes param", async () => {
    await CategoriesService.list("acme", false);
    expect(mockRequest).toHaveBeenCalledWith(
      "GET",
      "/v1/admin/document-categories?tenant_id=acme&active_only=false",
    );
  });

  it("list without tenantId", async () => {
    await CategoriesService.list(null);
    expect(mockRequest).toHaveBeenCalledWith("GET", "/v1/admin/document-categories");
  });

  it("create calls POST with body", async () => {
    mockRequest.mockResolvedValue({ categoryName: "tax-forms" });
    const result = await CategoriesService.create(
      "acme",
      "tax-forms",
      "Tax Forms",
      "All tax documents",
    );
    expect(mockRequest).toHaveBeenCalledWith(
      "POST",
      "/v1/admin/document-categories?tenant_id=acme",
      {
        category_name: "tax-forms",
        display_name: "Tax Forms",
        description: "All tax documents",
      },
    );
    expect(result.categoryName).toBe("tax-forms");
  });

  it("create with null description", async () => {
    await CategoriesService.create("acme", "misc", "Misc", null);
    expect(mockRequest).toHaveBeenCalledWith(
      "POST",
      "/v1/admin/document-categories?tenant_id=acme",
      {
        category_name: "misc",
        display_name: "Misc",
        description: null,
      },
    );
  });

  it("update calls PATCH with partial body", async () => {
    await CategoriesService.update("acme", "tax-forms", { displayName: "Updated" });
    expect(mockRequest).toHaveBeenCalledWith(
      "PATCH",
      "/v1/admin/document-categories/tax-forms?tenant_id=acme",
      { display_name: "Updated" },
    );
  });

  it("remove calls DELETE", async () => {
    await CategoriesService.remove("acme", "tax-forms");
    expect(mockRequest).toHaveBeenCalledWith(
      "DELETE",
      "/v1/admin/document-categories/tax-forms?tenant_id=acme",
    );
  });
});
