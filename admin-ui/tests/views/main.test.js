import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

function flush() {
  return new Promise((r) => setTimeout(r, 0));
}

describe("main.js router", () => {
  let Session, LoginView, KeysView, TenantContext, HttpClient;

  beforeEach(async () => {
    vi.resetModules();

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        json: () =>
          Promise.resolve({
            api_endpoint: { value: "http://localhost:8000" },
            cognito_user_pool_id: { value: "us-east-1_abc" },
            cognito_client_id: { value: "client123" },
          }),
      }),
    );

    vi.doMock("../../src/utils/session.js", () => ({
      get: vi.fn(() => null),
      save: vi.fn(),
      clear: vi.fn(),
      isExpired: vi.fn(() => true),
      isApproved: vi.fn(() => true),
      isSuperAdmin: vi.fn(() => false),
      onExpire: vi.fn(),
    }));
    vi.doMock("../../src/utils/toast.js", () => ({ show: vi.fn() }));
    vi.doMock("../../src/utils/tenant-context.js", () => ({
      init: vi.fn(),
      load: vi.fn(),
      getTenantId: vi.fn(() => null),
      onChange: vi.fn(() => () => {}),
    }));
    vi.doMock("../../src/services/http.js", () => ({
      adminClient: { request: vi.fn(), configure: vi.fn(), getBaseUrl: () => "" },
      dataClient: { request: vi.fn(), configure: vi.fn(), getBaseUrl: () => "" },
      configure: vi.fn(),
    }));
    vi.doMock("../../src/services/auth.js", () => ({
      configure: vi.fn(),
      signIn: vi.fn(),
      signOut: vi.fn(),
    }));

    const mockView = () => ({ mount: vi.fn(), unmount: vi.fn() });
    vi.doMock("../../src/views/keys/keys.js", () => ({ mount: vi.fn(), unmount: vi.fn() }));
    vi.doMock("../../src/views/extraction-rules/extraction-rules.js", mockView);
    vi.doMock("../../src/views/users/users.js", mockView);
    vi.doMock("../../src/views/tenants/tenants.js", mockView);
    vi.doMock("../../src/views/document-categories/document-categories.js", mockView);
    vi.doMock("../../src/views/audit-log/audit-log.js", mockView);
    vi.doMock("../../src/views/documents/documents.js", mockView);
    vi.doMock("../../src/views/test-documents/test-documents.js", mockView);
    vi.doMock("../../src/views/login/login.js", () => ({
      mount: vi.fn(),
      unmount: vi.fn(),
      onLoginSuccess: vi.fn(),
    }));

    vi.doMock("../../src/views/pending/pending.html", () => ({
      default: '<div id="pending-email"></div><button id="pending-logout-btn"></button>',
    }));
    vi.doMock("../../src/views/sidebar/sidebar.html", () => ({
      default: `<div id="connected-url"></div><select id="global-tenant-select"></select>
        <div id="main-content"></div><h2 id="view-title"></h2><div id="view-actions"></div>
        <button id="logout-btn"></button>
        <div class="nav-section"><button class="nav-section-header" data-section="keys"><span class="nav-arrow">▸</span></button><div class="nav-section-body hidden" id="section-keys"><a class="nav-item" data-view="keys">API Keys</a></div></div>
        <div class="nav-section" id="nav-section-users"><button class="nav-section-header" data-section="users"><span class="nav-arrow">▸</span></button><div class="nav-section-body hidden" id="section-users"><a class="nav-item" data-view="users">Users</a></div></div>
        <div class="nav-section" id="nav-section-tenants"><button class="nav-section-header" data-section="tenants"><span class="nav-arrow">▸</span></button><div class="nav-section-body hidden" id="section-tenants"><a class="nav-item" data-view="tenants">Tenants</a></div></div>`,
    }));

    document.body.innerHTML = '<div id="app"></div>';

    Session = await import("../../src/utils/session.js");
    LoginView = await import("../../src/views/login/login.js");
    KeysView = await import("../../src/views/keys/keys.js");
    TenantContext = await import("../../src/utils/tenant-context.js");
    HttpClient = await import("../../src/services/http.js");
  });

  afterEach(() => {
    document.body.innerHTML = "";
    location.hash = "";
    vi.unstubAllGlobals();
  });

  it("shows login when no session", async () => {
    Session.get.mockReturnValue(null);
    await import("../../src/main.js");
    await flush();
    expect(LoginView.mount).toHaveBeenCalled();
  });

  it("shows login when session expired", async () => {
    Session.get.mockReturnValue({ accessToken: "tok" });
    Session.isExpired.mockReturnValue(true);
    await import("../../src/main.js");
    await flush();
    expect(Session.clear).toHaveBeenCalled();
    expect(LoginView.mount).toHaveBeenCalled();
  });

  it("shows dashboard when session valid and approved", async () => {
    Session.get.mockReturnValue({ accessToken: "tok", idToken: "id", email: "a@b.com" });
    Session.isExpired.mockReturnValue(false);
    Session.isApproved.mockReturnValue(true);
    await import("../../src/main.js");
    await flush();

    // Dashboard rendered - keys view mounted as default
    expect(KeysView.mount).toHaveBeenCalled();
    expect(TenantContext.init).toHaveBeenCalled();
    expect(document.querySelector("#connected-url").textContent).toBe("a@b.com");
  });

  it("shows pending card when session valid but not approved", async () => {
    Session.get.mockReturnValue({ accessToken: "tok", idToken: "id", email: "pending@user.com" });
    Session.isExpired.mockReturnValue(false);
    Session.isApproved.mockReturnValue(false);
    await import("../../src/main.js");
    await flush();

    expect(document.querySelector("#pending-email").textContent).toBe("pending@user.com");
    expect(KeysView.mount).not.toHaveBeenCalled();
  });

  it("hides users/tenants nav for non-super-admin", async () => {
    Session.get.mockReturnValue({ accessToken: "tok", idToken: "id", email: "a@b.com" });
    Session.isExpired.mockReturnValue(false);
    Session.isApproved.mockReturnValue(true);
    Session.isSuperAdmin.mockReturnValue(false);
    await import("../../src/main.js");
    await flush();

    expect(document.querySelector("#nav-section-users").classList.contains("hidden")).toBe(true);
    expect(document.querySelector("#nav-section-tenants").classList.contains("hidden")).toBe(true);
  });

  it("shows users/tenants nav for super-admin", async () => {
    Session.get.mockReturnValue({ accessToken: "tok", idToken: "id", email: "a@b.com" });
    Session.isExpired.mockReturnValue(false);
    Session.isApproved.mockReturnValue(true);
    Session.isSuperAdmin.mockReturnValue(true);
    await import("../../src/main.js");
    await flush();

    expect(document.querySelector("#nav-section-users").classList.contains("hidden")).toBe(false);
    expect(document.querySelector("#nav-section-tenants").classList.contains("hidden")).toBe(false);
  });

  it("configures HTTP client with JWT on dashboard", async () => {
    Session.get.mockReturnValue({ accessToken: "tok", idToken: "my-jwt", email: "a@b.com" });
    Session.isExpired.mockReturnValue(false);
    Session.isApproved.mockReturnValue(true);
    await import("../../src/main.js");
    await flush();

    expect(HttpClient.configure).toHaveBeenCalledWith(
      expect.objectContaining({ baseUrl: "http://localhost:8000", jwt: "my-jwt" }),
    );
  });

  it("restores view from hash on refresh", async () => {
    location.hash = "#audit-log";
    Session.get.mockReturnValue({ accessToken: "tok", idToken: "id", email: "a@b.com" });
    Session.isExpired.mockReturnValue(false);
    Session.isApproved.mockReturnValue(true);

    // Add audit-log nav item to sidebar mock
    vi.doMock("../../src/views/sidebar/sidebar.html", () => ({
      default: `<div id="connected-url"></div><select id="global-tenant-select"></select>
        <div id="main-content"></div><h2 id="view-title"></h2><div id="view-actions"></div>
        <button id="logout-btn"></button>
        <div class="nav-section" id="nav-section-users"><button class="nav-section-header" data-section="users"><span class="nav-arrow">▸</span></button><div class="nav-section-body hidden" id="section-users"><a class="nav-item" data-view="users">Users</a></div></div>
        <div class="nav-section" id="nav-section-tenants"><button class="nav-section-header" data-section="tenants"><span class="nav-arrow">▸</span></button><div class="nav-section-body hidden" id="section-tenants"><a class="nav-item" data-view="tenants">Tenants</a></div></div>
        <div class="nav-section"><button class="nav-section-header" data-section="audit"><span class="nav-arrow">▸</span></button><div class="nav-section-body hidden" id="section-audit"><a class="nav-item" data-view="audit-log">Audit Log</a></div></div>`,
    }));

    const AuditLogView = await import("../../src/views/audit-log/audit-log.js");
    await import("../../src/main.js");
    await flush();

    expect(AuditLogView.mount).toHaveBeenCalled();
    expect(KeysView.mount).not.toHaveBeenCalled();
  });

  it("does not fire reportLogin on page refresh with valid session", async () => {
    Session.get.mockReturnValue({ accessToken: "tok", idToken: "id", email: "a@b.com" });
    Session.isExpired.mockReturnValue(false);
    Session.isApproved.mockReturnValue(true);

    vi.doMock("../../src/services/audit.js", () => ({
      reportLogin: vi.fn(),
      reportLogout: vi.fn(),
    }));
    const Audit = await import("../../src/services/audit.js");
    await import("../../src/main.js");
    await flush();

    expect(Audit.reportLogin).not.toHaveBeenCalled();
  });

  it("registers onLoginSuccess callback", async () => {
    await import("../../src/main.js");
    expect(LoginView.onLoginSuccess).toHaveBeenCalledWith(expect.any(Function));
  });

  it("registers session expiry handler", async () => {
    await import("../../src/main.js");
    expect(Session.onExpire).toHaveBeenCalledWith(expect.any(Function));
  });
});
