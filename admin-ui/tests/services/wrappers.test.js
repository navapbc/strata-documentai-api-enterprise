import { describe, it, expect, beforeEach, vi } from "vitest";

let KeysService, DocumentsService, TenantsService, AuditLogService;

describe("service wrappers", () => {
  let mockRequest;

  beforeEach(async () => {
    vi.resetModules();

    // Mock the adminClient.request
    mockRequest = vi.fn().mockResolvedValue({});
    vi.doMock("../../src/services/http.js", () => ({
      adminClient: { request: mockRequest, configure: vi.fn(), getBaseUrl: () => "" },
      dataClient: { request: mockRequest, configure: vi.fn(), getBaseUrl: () => "" },
    }));

    KeysService = await import("../../src/services/keys.js");
    DocumentsService = await import("../../src/services/documents.js");
    TenantsService = await import("../../src/services/tenants.js");
    AuditLogService = await import("../../src/services/audit-log.js");
  });

  describe("keys service", () => {
    it("list calls GET /v1/admin/api-keys", async () => {
      mockRequest.mockResolvedValue({ keys: [{ keyPrefix: "abc" }] });
      const result = await KeysService.list({ tenantId: "acme" });
      expect(mockRequest).toHaveBeenCalledWith("GET", "/v1/admin/api-keys?tenant_id=acme");
      expect(result.keys).toHaveLength(1);
    });

    it("list with includeInactive", async () => {
      await KeysService.list({ includeInactive: true, tenantId: "acme" });
      expect(mockRequest).toHaveBeenCalledWith(
        "GET",
        "/v1/admin/api-keys?include_inactive=true&tenant_id=acme",
      );
    });

    it("create calls POST with body", async () => {
      mockRequest.mockResolvedValue({ apiKey: "generated-key" });
      const result = await KeysService.create("my-key", "dev", undefined, "a@b.com", "acme");
      expect(mockRequest).toHaveBeenCalledWith("POST", "/v1/admin/api-keys", {
        api_key_name: "my-key",
        environment: "dev",
        email_address: "a@b.com",
        tenant_id: "acme",
      });
      expect(result.apiKey).toBe("generated-key");
    });

    it("revoke calls DELETE with prefix", async () => {
      await KeysService.revoke("abc123");
      expect(mockRequest).toHaveBeenCalledWith("DELETE", "/v1/admin/api-keys/abc123");
    });
  });

  describe("documents service", () => {
    it("list calls GET with tenant_id", async () => {
      mockRequest.mockResolvedValue({ documents: [{ jobId: "j1" }], nextCursor: "c1" });
      const result = await DocumentsService.list({ tenantId: "acme", limit: 50 });
      expect(mockRequest).toHaveBeenCalledWith(
        "GET",
        "/v1/admin/documents?tenant_id=acme&limit=50",
      );
      expect(result.documents).toHaveLength(1);
      expect(result.nextCursor).toBe("c1");
    });

    it("get calls GET with job ID", async () => {
      mockRequest.mockResolvedValue({ jobId: "job-123", fileName: "w2.pdf" });
      const result = await DocumentsService.get("job-123");
      expect(mockRequest).toHaveBeenCalledWith("GET", "/v1/admin/documents/job-123");
      expect(result.fileName).toBe("w2.pdf");
    });
  });

  describe("tenants service", () => {
    it("list calls GET /v1/admin/tenants", async () => {
      await TenantsService.list();
      expect(mockRequest).toHaveBeenCalledWith("GET", "/v1/admin/tenants");
    });

    it("create calls POST with body", async () => {
      mockRequest.mockResolvedValue({ tenantId: "acme" });
      const result = await TenantsService.create("acme", "Acme Corp", "ops@acme.com");
      expect(mockRequest).toHaveBeenCalledWith("POST", "/v1/admin/tenants", {
        tenant_id: "acme",
        display_name: "Acme Corp",
        primary_contact: "ops@acme.com",
      });
      expect(result.tenantId).toBe("acme");
    });

    it("remove calls DELETE", async () => {
      await TenantsService.remove("acme");
      expect(mockRequest).toHaveBeenCalledWith("DELETE", "/v1/admin/tenants/acme");
    });
  });

  describe("audit-log service", () => {
    it("list calls GET with filters", async () => {
      mockRequest.mockResolvedValue({ events: [{ action: "key.create" }] });
      const result = await AuditLogService.list({ tenantId: "acme", action: "key.create" });
      expect(mockRequest).toHaveBeenCalledWith(
        "GET",
        "/v1/admin/audit-log?tenant_id=acme&action=key.create",
      );
      expect(result.events[0].action).toBe("key.create");
    });

    it("listActions calls GET /actions", async () => {
      await AuditLogService.listActions();
      expect(mockRequest).toHaveBeenCalledWith("GET", "/v1/admin/audit-log/actions");
    });
  });
});
