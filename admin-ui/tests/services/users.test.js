import { describe, it, expect, beforeEach, vi } from "vitest";

describe("users service", () => {
  let mockRequest, UsersService;

  beforeEach(async () => {
    vi.resetModules();
    mockRequest = vi.fn().mockResolvedValue({});
    vi.doMock("../../src/services/http.js", () => ({
      adminClient: { request: mockRequest, configure: vi.fn(), getBaseUrl: () => "" },
      dataClient: { request: mockRequest, configure: vi.fn(), getBaseUrl: () => "" },
    }));
    UsersService = await import("../../src/services/users.js");
  });

  it("list calls GET /v1/admin/users", async () => {
    mockRequest.mockResolvedValue({ users: [{ email: "a@b.com" }] });
    const result = await UsersService.list();
    expect(mockRequest).toHaveBeenCalledWith("GET", "/v1/admin/users");
    expect(result.users).toHaveLength(1);
  });

  it("approve calls POST with role and tenant_id", async () => {
    mockRequest.mockResolvedValue({ success: true });
    const result = await UsersService.approve("user-123", "tenant-admin", "acme");
    expect(mockRequest).toHaveBeenCalledWith("POST", "/v1/admin/users/user-123/approve", {
      role: "tenant-admin",
      tenant_id: "acme",
    });
    expect(result.success).toBe(true);
  });

  it("approve with null tenant_id", async () => {
    await UsersService.approve("user-123", "super-admin", null);
    expect(mockRequest).toHaveBeenCalledWith("POST", "/v1/admin/users/user-123/approve", {
      role: "super-admin",
      tenant_id: null,
    });
  });

  it("changeRole calls POST /role", async () => {
    await UsersService.changeRole("user-123", "super-admin");
    expect(mockRequest).toHaveBeenCalledWith("POST", "/v1/admin/users/user-123/role", {
      role: "super-admin",
    });
  });

  it("changeTenant calls POST /tenant", async () => {
    await UsersService.changeTenant("user-123", "acme");
    expect(mockRequest).toHaveBeenCalledWith("POST", "/v1/admin/users/user-123/tenant", {
      tenant_id: "acme",
    });
  });

  it("remove calls DELETE", async () => {
    mockRequest.mockResolvedValue({ deleted: true });
    const result = await UsersService.remove("user-123");
    expect(mockRequest).toHaveBeenCalledWith("DELETE", "/v1/admin/users/user-123");
    expect(result).toEqual({ deleted: true });
  });

  it("encodes username with special chars", async () => {
    await UsersService.remove("user@example.com");
    expect(mockRequest).toHaveBeenCalledWith("DELETE", "/v1/admin/users/user%40example.com");
  });
});
