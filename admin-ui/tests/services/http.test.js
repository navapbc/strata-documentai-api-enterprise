import { describe, it, expect, beforeEach, vi } from "vitest";

let adminClient, dataClient;

describe("http client", () => {
  beforeEach(async () => {
    vi.resetModules();
    sessionStorage.clear();
    sessionStorage.setItem(
      "docai_console_session",
      JSON.stringify({ accessToken: "old", email: "a@b.com", expiresAt: Date.now() + 60000 }),
    );
    delete window.location;
    window.location = { reload: vi.fn() };
    global.fetch = vi.fn();

    const mod = await import("../../src/services/http.js");
    adminClient = mod.adminClient;
    dataClient = mod.dataClient;
    mod.configure({ baseUrl: "http://localhost:8000", jwt: "test-jwt", apiKey: "test-key" });
  });

  describe("401 handling", () => {
    it("clears session and reloads on 401", async () => {
      global.fetch.mockResolvedValue({ ok: false, status: 401, statusText: "Unauthorized" });

      const result = await adminClient.request("GET", "/v1/admin/api-keys");

      expect(result).toBeUndefined();
      expect(sessionStorage.getItem("docai_console_session")).toBeNull();
      expect(window.location.reload).toHaveBeenCalled();
    });

    it("does not clear session on 403", async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        status: 403,
        statusText: "Forbidden",
        json: () => Promise.resolve({ detail: "Access denied" }),
      });

      await expect(adminClient.request("GET", "/v1/admin/tenants")).rejects.toThrow(
        "Access denied",
      );
      expect(sessionStorage.getItem("docai_console_session")).not.toBeNull();
    });
  });

  describe("happy path", () => {
    it("returns parsed JSON on success", async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ keys: [] }),
      });

      const result = await adminClient.request("GET", "/v1/admin/api-keys");
      expect(result).toEqual({ keys: [] });
    });

    it("sends correct URL", async () => {
      global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });

      await adminClient.request("GET", "/v1/test");

      expect(global.fetch).toHaveBeenCalledWith(
        "http://localhost:8000/v1/test",
        expect.any(Object),
      );
    });
  });

  describe("request headers", () => {
    it("adminClient sends Bearer token", async () => {
      global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });

      await adminClient.request("GET", "/v1/admin/keys");

      const opts = global.fetch.mock.calls[0][1];
      expect(opts.headers.Authorization).toBe("Bearer test-jwt");
    });

    it("dataClient sends API-Key header", async () => {
      global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });

      await dataClient.request("GET", "/v1/documents");

      const opts = global.fetch.mock.calls[0][1];
      expect(opts.headers["API-Key"]).toBe("test-key");
    });
  });

  describe("POST body", () => {
    it("serializes body as JSON", async () => {
      global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });

      await adminClient.request("POST", "/v1/admin/tenants", { tenant_id: "acme" });

      const opts = global.fetch.mock.calls[0][1];
      expect(opts.method).toBe("POST");
      expect(opts.body).toBe('{"tenant_id":"acme"}');
      expect(opts.headers["Content-Type"]).toBe("application/json");
    });
  });

  describe("network error", () => {
    it("throws readable error on fetch failure", async () => {
      global.fetch.mockRejectedValue(new TypeError("Failed to fetch"));

      await expect(adminClient.request("GET", "/v1/test")).rejects.toThrow("Cannot reach API");
    });
  });

  describe("non-JSON error body", () => {
    it("falls back to statusText", async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
        json: () => Promise.reject(new Error("not json")),
      });

      await expect(adminClient.request("GET", "/v1/test")).rejects.toThrow("Internal Server Error");
    });
  });
});

describe("error properties", () => {
  beforeEach(async () => {
    vi.resetModules();
    global.fetch = vi.fn();
    delete window.location;
    window.location = { reload: vi.fn() };
    const mod = await import("../../src/services/http.js");
    adminClient = mod.adminClient;
    mod.configure({ baseUrl: "http://localhost:8000", jwt: "t", apiKey: "k" });
  });

  it("attaches status, method, path to thrown error", async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 403,
      statusText: "Forbidden",
      json: () => Promise.resolve({ detail: "Nope" }),
    });

    try {
      await adminClient.request("POST", "/v1/admin/tenants");
      expect.fail("should have thrown");
    } catch (e) {
      expect(e.status).toBe(403);
      expect(e.method).toBe("POST");
      expect(e.path).toBe("/v1/admin/tenants");
      expect(e.message).toBe("Nope");
    }
  });
});
