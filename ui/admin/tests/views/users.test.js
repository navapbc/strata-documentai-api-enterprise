import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { buildUser } from "../factories.js";

let UsersView, mockUsersList, mockApprove, mockRemove, mockTenantsList, mockToast;

function flush() {
  return new Promise((r) => setTimeout(r, 0));
}

describe("users view", () => {
  let root;

  beforeEach(async () => {
    vi.resetModules();

    mockUsersList = vi.fn().mockResolvedValue({ users: [] });
    mockApprove = vi.fn().mockResolvedValue({});
    mockRemove = vi.fn().mockResolvedValue({});
    mockTenantsList = vi
      .fn()
      .mockResolvedValue({ tenants: [{ tenantId: "acme", displayName: "Acme" }] });
    mockToast = { show: vi.fn() };

    vi.doMock("../../src/services/users.js", () => ({
      list: mockUsersList,
      approve: mockApprove,
      remove: mockRemove,
    }));
    vi.doMock("../../src/services/tenants.js", () => ({ list: mockTenantsList }));
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

    UsersView = await import("../../src/views/users/users.js");
    root = document.createElement("div");
    document.body.appendChild(root);
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("mounts and loads users", async () => {
    UsersView.mount(root);
    await flush();
    expect(mockUsersList).toHaveBeenCalled();
  });

  it("renders user rows with role badges", async () => {
    mockUsersList.mockResolvedValue({
      users: [
        buildUser({ groups: ["super-admin"] }),
        buildUser({ email: "other@co.com", username: "u2", groups: [] }),
      ],
    });
    UsersView.mount(root);
    await flush();
    expect(root.querySelectorAll("#users-tbody tr").length).toBe(2);
    expect(root.querySelector(".badge-success")).toBeTruthy();
    expect(root.querySelector(".badge-neutral")).toBeTruthy();
  });

  // --- Assign Role ---

  it("assign role button opens modal with user email", async () => {
    const user = buildUser();
    mockUsersList.mockResolvedValue({ users: [user] });
    UsersView.mount(root);
    await flush();

    root.querySelector("#users-tbody .btn-secondary").click();
    await flush();

    expect(root.querySelector("#assign-role-modal").classList.contains("hidden")).toBe(false);
    expect(root.querySelector("#assign-role-email").textContent).toBe(user.email);
  });

  it("assign role form submits and calls approve", async () => {
    const user = buildUser();
    mockUsersList.mockResolvedValue({ users: [user] });
    UsersView.mount(root);
    await flush();

    root.querySelector("#users-tbody .btn-secondary").click();
    await flush();

    root.querySelector("#assign-role").value = "super-admin";
    root
      .querySelector("#assign-role-form")
      .dispatchEvent(new Event("submit", { cancelable: true }));
    await flush();

    expect(mockApprove).toHaveBeenCalledWith(user.username, "super-admin", "");
    expect(mockToast.show).toHaveBeenCalledWith("Role assigned");
    expect(root.querySelector("#assign-role-modal").classList.contains("hidden")).toBe(true);
  });

  it("cancel assign role closes modal", async () => {
    mockUsersList.mockResolvedValue({ users: [buildUser()] });
    UsersView.mount(root);
    await flush();

    root.querySelector("#users-tbody .btn-secondary").click();
    await flush();
    root.querySelector("#assign-role-cancel").click();

    expect(root.querySelector("#assign-role-modal").classList.contains("hidden")).toBe(true);
    expect(mockApprove).not.toHaveBeenCalled();
  });

  // --- Delete User ---

  it("delete button opens delete modal", async () => {
    const user = buildUser();
    mockUsersList.mockResolvedValue({ users: [user] });
    UsersView.mount(root);
    await flush();

    root.querySelector("#users-tbody .btn-outline-danger").click();
    expect(root.querySelector("#delete-user-modal").classList.contains("hidden")).toBe(false);
    expect(root.querySelector("#delete-user-email").textContent).toBe(user.email);
  });

  it("confirm delete calls remove and reloads", async () => {
    const user = buildUser();
    mockUsersList.mockResolvedValue({ users: [user] });
    UsersView.mount(root);
    await flush();

    root.querySelector("#users-tbody .btn-outline-danger").click();
    root.querySelector("#delete-user-confirm").click();
    await flush();

    expect(mockRemove).toHaveBeenCalledWith(user.username);
    expect(mockToast.show).toHaveBeenCalledWith("User deleted");
  });

  it("cancel delete closes modal", async () => {
    mockUsersList.mockResolvedValue({ users: [buildUser()] });
    UsersView.mount(root);
    await flush();

    root.querySelector("#users-tbody .btn-outline-danger").click();
    root.querySelector("#delete-user-cancel").click();

    expect(root.querySelector("#delete-user-modal").classList.contains("hidden")).toBe(true);
    expect(mockRemove).not.toHaveBeenCalled();
  });

  it("unmount clears root", () => {
    UsersView.mount(root);
    UsersView.unmount(root);
    expect(root.children.length).toBe(0);
  });
});
