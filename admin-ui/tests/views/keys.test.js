import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { buildApiKey, buildTenant } from "../factories.js";

let KeysView, mockKeysList, mockKeysCreate, mockKeysRevoke, mockGetTenantId;

const { tenantId: TENANT_ID } = buildTenant();

function flush() {
  return new Promise((r) => setTimeout(r, 0));
}

describe("keys view", () => {
  let root;

  beforeEach(async () => {
    vi.resetModules();

    mockKeysList = vi.fn().mockResolvedValue({ keys: [] });
    mockKeysCreate = vi.fn().mockResolvedValue({ apiKey: "new-key-abc123" });
    mockKeysRevoke = vi.fn().mockResolvedValue({});
    mockGetTenantId = vi.fn().mockReturnValue(TENANT_ID);

    vi.doMock("../../src/services/keys.js", () => ({
      list: mockKeysList,
      create: mockKeysCreate,
      revoke: mockKeysRevoke,
    }));
    vi.doMock("../../src/utils/tenant-context.js", () => ({
      getTenantId: mockGetTenantId,
      onChange: vi.fn(() => () => {}),
    }));
    vi.doMock("../../src/utils/helpers.js", () => ({
      esc: (s) => s,
      formatDate: (d) => d || "-",
      showLoading: vi.fn(),
      setViewActions: vi.fn(),
      clearViewActions: vi.fn(),
      bindSortHeaders: vi.fn(() => () => {}),
      sortRows: (rows) => rows,
    }));

    // Mock global tenant select for openCreateModal
    const globalSelect = document.createElement("select");
    globalSelect.id = "global-tenant-select";
    const opt = document.createElement("option");
    opt.value = TENANT_ID;
    opt.textContent = "Acme Corp";
    globalSelect.appendChild(opt);
    document.body.appendChild(globalSelect);

    KeysView = await import("../../src/views/keys/keys.js");
    root = document.createElement("div");
    document.body.appendChild(root);
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  // --- Render ---

  it("mounts and calls list on load", async () => {
    KeysView.mount(root);
    await flush();
    expect(mockKeysList).toHaveBeenCalledWith({ includeInactive: false, tenantId: TENANT_ID });
  });

  it("renders keys in table", () => {
    KeysView.mount(root);
    KeysView.render([buildApiKey()]);
    expect(root.querySelectorAll("#keys-tbody tr").length).toBe(1);
    expect(root.querySelector("#no-keys").classList.contains("hidden")).toBe(true);
  });

  it("shows no-keys message when empty", () => {
    KeysView.mount(root);
    KeysView.render([]);
    expect(root.querySelector("#no-keys").classList.contains("hidden")).toBe(false);
  });

  it("revoked keys show badge instead of revoke button", () => {
    KeysView.mount(root);
    KeysView.render([buildApiKey({ isActive: false })]);
    const tbody = root.querySelector("#keys-tbody");
    expect(tbody.querySelector(".badge-revoked")).toBeTruthy();
    expect(tbody.querySelector(".btn-outline-danger")).toBeFalsy();
  });

  // --- Revoke interaction ---

  it("clicking revoke button opens revoke modal", () => {
    const key = buildApiKey();
    KeysView.mount(root);
    KeysView.render([key]);

    root.querySelector(".btn-outline-danger").click();

    const modal = root.querySelector("#revoke-modal");
    expect(modal.classList.contains("hidden")).toBe(false);
    expect(root.querySelector("#revoke-key-prefix").textContent).toBe(key.keyPrefix);
  });

  it("confirm revoke calls service and reloads", async () => {
    const key = buildApiKey();
    mockKeysList.mockResolvedValue({ keys: [key] });
    KeysView.mount(root);
    await flush();

    root.querySelector(".btn-outline-danger").click();
    root.querySelector("#confirm-revoke").click();
    await flush();

    expect(mockKeysRevoke).toHaveBeenCalledWith(key.keyPrefix);
    expect(mockKeysList).toHaveBeenCalledTimes(2);
  });

  it("cancel revoke closes modal without calling service", () => {
    KeysView.mount(root);
    KeysView.render([buildApiKey()]);

    root.querySelector(".btn-outline-danger").click();
    root.querySelector("#cancel-revoke").click();

    expect(root.querySelector("#revoke-modal").classList.contains("hidden")).toBe(true);
    expect(mockKeysRevoke).not.toHaveBeenCalled();
  });

  // --- Create interaction ---

  it("create form submits and shows new key", async () => {
    KeysView.mount(root);
    await flush();

    const tenantSelect = root.querySelector("#key-tenant");
    const opt = document.createElement("option");
    opt.value = TENANT_ID;
    opt.textContent = "Test Tenant";
    tenantSelect.appendChild(opt);
    tenantSelect.value = TENANT_ID;

    root.querySelector("#api-key-name").value = "my-new-key";
    root.querySelector("#client-environment").value = "prod";
    root.querySelector("#client-email").value = "dev@co.com";
    root.querySelector("#create-form").dispatchEvent(new Event("submit", { cancelable: true }));
    await flush();

    expect(mockKeysCreate).toHaveBeenCalledWith(
      "my-new-key",
      "prod",
      undefined,
      "dev@co.com",
      TENANT_ID,
    );
    expect(root.querySelector("#new-key-value").textContent).toBe("new-key-abc123");
    expect(root.querySelector("#key-created-modal").classList.contains("hidden")).toBe(false);
  });

  it("close-created button hides key modal", async () => {
    KeysView.mount(root);
    root.querySelector("#key-created-modal").classList.remove("hidden");
    root.querySelector("#close-created").click();
    expect(root.querySelector("#key-created-modal").classList.contains("hidden")).toBe(true);
  });

  // --- Cleanup ---

  it("unmount cleans up", () => {
    KeysView.mount(root);
    KeysView.unmount(root);
    expect(root.children.length).toBe(0);
  });
});
