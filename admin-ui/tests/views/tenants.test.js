import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { buildTenant } from "../factories.js";

let TenantsView, mockList, mockCreate, mockUpdate, mockRemove, mockToast;

function flush() {
  return new Promise((r) => setTimeout(r, 0));
}

function submitTenantForm(root, id, name, contact = "") {
  if (id !== undefined) root.querySelector("#tenant-id").value = id;
  root.querySelector("#tenant-name").value = name;
  root.querySelector("#tenant-contact").value = contact;
  root.querySelector("#tenant-form").dispatchEvent(new Event("submit", { cancelable: true }));
}

describe("tenants view", () => {
  let root;

  beforeEach(async () => {
    vi.resetModules();

    mockList = vi.fn().mockResolvedValue({ tenants: [] });
    mockCreate = vi.fn().mockResolvedValue({});
    mockUpdate = vi.fn().mockResolvedValue({});
    mockRemove = vi.fn().mockResolvedValue({});
    mockToast = { show: vi.fn() };

    vi.doMock("../../src/services/tenants.js", () => ({
      list: mockList,
      create: mockCreate,
      update: mockUpdate,
      remove: mockRemove,
    }));
    vi.doMock("../../src/utils/tenant-context.js", () => ({
      getTenantId: vi.fn(() => null),
      onChange: vi.fn(() => () => {}),
      load: vi.fn(),
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
    vi.doMock("../../src/utils/toast.js", () => mockToast);

    TenantsView = await import("../../src/views/tenants/tenants.js");
    root = document.createElement("div");
    document.body.appendChild(root);
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("mounts and loads tenants", async () => {
    TenantsView.mount(root);
    await flush();
    expect(mockList).toHaveBeenCalled();
  });

  it("renders tenant rows", async () => {
    mockList.mockResolvedValue({ tenants: [buildTenant()] });
    TenantsView.mount(root);
    await flush();
    expect(root.querySelectorAll("#tenants-tbody tr").length).toBe(1);
  });

  it("shows no-tenants when empty", async () => {
    TenantsView.mount(root);
    await flush();
    expect(root.querySelector("#no-tenants").classList.contains("hidden")).toBe(false);
  });

  // --- Create ---

  it("create form submits and calls service", async () => {
    TenantsView.mount(root);
    await flush();

    submitTenantForm(root, "new-co", "New Company", "ops@new.co");
    await flush();

    expect(mockCreate).toHaveBeenCalledWith("new-co", "New Company", "ops@new.co");
    expect(mockToast.show).toHaveBeenCalledWith("Tenant created");
    expect(root.querySelector("#tenant-modal").classList.contains("hidden")).toBe(true);
    expect(mockList).toHaveBeenCalledTimes(2);
  });

  it("create form shows error on failure", async () => {
    mockCreate.mockRejectedValue(new Error("Duplicate tenant"));
    TenantsView.mount(root);
    await flush();

    submitTenantForm(root, "dup", "Dup");
    await flush();

    const error = root.querySelector("#tenant-form-error");
    expect(error.classList.contains("hidden")).toBe(false);
    expect(error.textContent).toBe("Duplicate tenant");
  });

  // --- Edit ---

  it("edit button opens modal with pre-filled values", async () => {
    const tenant = buildTenant();
    mockList.mockResolvedValue({ tenants: [tenant] });
    TenantsView.mount(root);
    await flush();

    root.querySelector(".btn-secondary").click();
    expect(root.querySelector("#tenant-modal").classList.contains("hidden")).toBe(false);
    expect(root.querySelector("#tenant-id").value).toBe(tenant.tenantId);
    expect(root.querySelector("#tenant-id").disabled).toBe(true);
    expect(root.querySelector("#tenant-name").value).toBe(tenant.displayName);
  });

  it("edit form submits update", async () => {
    const tenant = buildTenant();
    mockList.mockResolvedValue({ tenants: [tenant] });
    TenantsView.mount(root);
    await flush();

    root.querySelector(".btn-secondary").click();
    submitTenantForm(root, undefined, "Updated Name", "new@co.com");
    await flush();

    expect(mockUpdate).toHaveBeenCalledWith(tenant.tenantId, {
      displayName: "Updated Name",
      primaryContact: "new@co.com",
    });
    expect(mockToast.show).toHaveBeenCalledWith("Tenant updated");
  });

  // --- Deactivate ---

  it("deactivate button opens delete modal", async () => {
    const tenant = buildTenant();
    mockList.mockResolvedValue({ tenants: [tenant] });
    TenantsView.mount(root);
    await flush();

    root.querySelector(".btn-outline-danger").click();
    expect(root.querySelector("#tenant-delete-modal").classList.contains("hidden")).toBe(false);
    expect(root.querySelector("#tenant-delete-name").textContent).toBe(tenant.displayName);
  });

  it("confirm deactivate calls remove and reloads", async () => {
    const tenant = buildTenant();
    mockList.mockResolvedValue({ tenants: [tenant] });
    TenantsView.mount(root);
    await flush();

    root.querySelector(".btn-outline-danger").click();
    root.querySelector("#tenant-delete-confirm").click();
    await flush();

    expect(mockRemove).toHaveBeenCalledWith(tenant.tenantId);
    expect(mockToast.show).toHaveBeenCalledWith("Tenant deactivated");
  });

  it("cancel deactivate closes modal", async () => {
    mockList.mockResolvedValue({ tenants: [buildTenant()] });
    TenantsView.mount(root);
    await flush();

    root.querySelector(".btn-outline-danger").click();
    root.querySelector("#tenant-delete-cancel").click();
    expect(root.querySelector("#tenant-delete-modal").classList.contains("hidden")).toBe(true);
    expect(mockRemove).not.toHaveBeenCalled();
  });

  // --- Cancel ---

  it("cancel button closes create modal", () => {
    TenantsView.mount(root);
    root.querySelector("#tenant-modal").classList.remove("hidden");
    root.querySelector("#tenant-cancel").click();
    expect(root.querySelector("#tenant-modal").classList.contains("hidden")).toBe(true);
  });

  it("unmount clears root", () => {
    TenantsView.mount(root);
    TenantsView.unmount(root);
    expect(root.children.length).toBe(0);
  });
});
