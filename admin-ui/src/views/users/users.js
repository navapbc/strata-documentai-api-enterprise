import * as UsersService from "../../services/users.js";
import * as TenantsService from "../../services/tenants.js";
import * as Helpers from "../../utils/helpers.js";
import * as Toast from "../../utils/toast.js";
import { h } from "../../utils/dom.js";
import { tpl } from "../../utils/tpl.js";
import html from "./users.html";

const tmpl = tpl(html);

let _root, _tbody, _noUsers, _refreshBtn, _showPendingOnly;
let _assignModal, _assignForm, _assignRoleSelect, _assignTenantSelect;
let _assignRoleEmail, _assignRoleError, _assignRoleCancel, _assignRoleTitle;
let _deleteModal, _deleteEmail, _deleteError, _deleteCancel, _deleteConfirm;
let _pendingUsername = null;

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  // Inject actions into shared header
  _showPendingOnly = h("input", { type: "checkbox", id: "show-pending-only" });
  _refreshBtn = h("button", { className: "btn-secondary" }, "Refresh");
  const label = h(
    "label",
    { className: "inline-checkbox" },
    _showPendingOnly,
    document.createTextNode(" Pending only"),
  );
  Helpers.setViewActions(label, _refreshBtn);

  _tbody = root.querySelector("#users-tbody");
  _noUsers = root.querySelector("#no-users");

  _assignModal = root.querySelector("#assign-role-modal");
  _assignForm = root.querySelector("#assign-role-form");
  _assignRoleSelect = root.querySelector("#assign-role");
  _assignTenantSelect = root.querySelector("#assign-tenant");
  _assignRoleEmail = root.querySelector("#assign-role-email");
  _assignRoleError = root.querySelector("#assign-role-error");
  _assignRoleCancel = root.querySelector("#assign-role-cancel");
  _assignRoleTitle = root.querySelector("#assign-role-title");

  _deleteModal = root.querySelector("#delete-user-modal");
  _deleteEmail = root.querySelector("#delete-user-email");
  _deleteError = root.querySelector("#delete-user-error");
  _deleteCancel = root.querySelector("#delete-user-cancel");
  _deleteConfirm = root.querySelector("#delete-user-confirm");

  _refreshBtn.addEventListener("click", () => load());
  _showPendingOnly.addEventListener("change", () => load());
  _assignRoleCancel.addEventListener("click", closeAssignModal);
  _assignForm.addEventListener("submit", handleAssignRole);
  _assignRoleSelect.addEventListener("change", toggleTenantRow);
  _deleteCancel.addEventListener("click", closeDeleteModal);
  _deleteConfirm.addEventListener("click", handleDeleteUser);

  load();
}

export function unmount(root) {
  root.replaceChildren();
}

export async function load() {
  Helpers.showLoading(_tbody, _noUsers);
  try {
    const data = await UsersService.list();
    renderTable(data.users || []);
  } catch (e) {
    _tbody.innerHTML = "";
    _noUsers.textContent = e.message;
    _noUsers.classList.remove("hidden");
  }
}

function renderTable(users) {
  const pendingOnly = _showPendingOnly?.checked;
  const filtered = pendingOnly ? users.filter((u) => !u.groups || u.groups.length === 0) : users;

  _tbody.innerHTML = "";
  if (filtered.length === 0) {
    _noUsers.classList.remove("hidden");
    return;
  }
  _noUsers.classList.add("hidden");

  for (const user of filtered) {
    const groups = user.groups || [];
    const role = groups[0] || "pending";
    const statusEl =
      groups.length > 0
        ? h("span", { className: "badge badge-success" }, "Active")
        : h("span", { className: "badge badge-neutral" }, "Pending");
    const roleBtn = h("button", { className: "btn-sm btn-secondary" }, "Assign Role");
    const deleteBtn = h("button", { className: "btn-sm btn-danger" }, "Delete");

    const tr = h(
      "tr",
      null,
      h("td", null, user.email || "-"),
      h("td", null, statusEl),
      h("td", null, role),
      h("td", null, user.tenantId || "-"),
      h("td", null, Helpers.formatDate(user.createdAt)),
      h("td", null, roleBtn, deleteBtn),
    );

    roleBtn.addEventListener("click", () => openAssignModal(user));
    deleteBtn.addEventListener("click", () => openDeleteModal(user));
    _tbody.appendChild(tr);
  }
}

async function openAssignModal(user) {
  _pendingUsername = user.username;
  _assignRoleEmail.textContent = user.email;
  _assignRoleError.classList.add("hidden");
  _assignRoleTitle.textContent = user.groups?.length > 0 ? "Change role" : "Approve user";

  // Load tenants for dropdown
  try {
    const data = await TenantsService.list();
    _assignTenantSelect.innerHTML = '<option value="">- Select a tenant -</option>';
    for (const t of data.tenants || []) {
      const opt = document.createElement("option");
      opt.value = t.tenantId;
      opt.textContent = t.displayName || t.tenantId;
      if (t.tenantId === user.tenantId) opt.selected = true;
      _assignTenantSelect.appendChild(opt);
    }
  } catch {
    /* leave empty */
  }

  if (user.groups?.length > 0) {
    _assignRoleSelect.value = user.groups[0];
  }
  toggleTenantRow();
  _assignModal.classList.remove("hidden");
}

function closeAssignModal() {
  _assignModal.classList.add("hidden");
  _pendingUsername = null;
}

function toggleTenantRow() {
  const row = _root.querySelector("#assign-tenant-row");
  row.style.display = _assignRoleSelect.value === "tenant-admin" ? "" : "none";
}

async function handleAssignRole(e) {
  e.preventDefault();
  _assignRoleError.classList.add("hidden");

  const role = _assignRoleSelect.value;
  const tenantId = _assignTenantSelect.value;

  if (role === "tenant-admin" && !tenantId) {
    _assignRoleError.textContent = "Tenant is required for tenant-admin role.";
    _assignRoleError.classList.remove("hidden");
    return;
  }

  try {
    await UsersService.approve(_pendingUsername, role, tenantId);
    closeAssignModal();
    Toast.show("Role assigned");
    load();
  } catch (err) {
    _assignRoleError.textContent = err.message;
    _assignRoleError.classList.remove("hidden");
  }
}

function openDeleteModal(user) {
  _pendingUsername = user.username;
  _deleteEmail.textContent = user.email;
  _deleteError.classList.add("hidden");
  _deleteModal.classList.remove("hidden");
}

function closeDeleteModal() {
  _deleteModal.classList.add("hidden");
  _pendingUsername = null;
}

async function handleDeleteUser() {
  _deleteError.classList.add("hidden");
  try {
    await UsersService.remove(_pendingUsername);
    closeDeleteModal();
    Toast.show("User deleted");
    load();
  } catch (err) {
    _deleteError.textContent = err.message;
    _deleteError.classList.remove("hidden");
  }
}
