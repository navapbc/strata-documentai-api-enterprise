import * as UsersService from "../../services/users.js";
import * as TenantsService from "../../services/tenants.js";
import * as Helpers from "../../utils/helpers.js";
import * as TenantContext from "../../utils/tenant-context.js";
import { openModal, closeModal } from "../../utils/modal.js";
import * as Toast from "../../utils/toast.js";
import { h, iconBtn } from "../../utils/dom.js";
import { tpl } from "../../utils/tpl.js";
import { TableView } from "../../utils/table-view.js";
import html from "./users.html";

const tmpl = tpl(html);

let _root, _tableView;
let _emailFilter, _roleFilter, _statusFilter;
let _assignModal, _assignForm, _assignRoleSelect, _assignTenantSelect;
let _assignRoleEmail, _assignRoleError, _assignRoleCancel, _assignRoleTitle;
let _deleteModal, _deleteEmail, _deleteError, _deleteCancel, _deleteConfirm;
let _pendingUsername = null;
let _allUsers = [];
let _tenantUnsub = null;

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  Helpers.setViewActions();
  _emailFilter = root.querySelector("#users-email-filter");
  _roleFilter = root.querySelector("#users-role-filter");
  _statusFilter = root.querySelector("#users-status-filter");

  _tableView = new TableView(
    root.querySelector("#users-table"),
    root.querySelector("#users-tbody"),
    root.querySelector("#no-users"),
    renderRow,
  ).bindSortHeaders(root.querySelector("thead"));

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

  _emailFilter.addEventListener("input", applyFilters);
  _roleFilter.addEventListener("change", applyFilters);
  _statusFilter.addEventListener("change", applyFilters);
  _assignRoleCancel.addEventListener("click", closeAssignModal);
  _assignForm.addEventListener("submit", handleAssignRole);
  _assignRoleSelect.addEventListener("change", toggleTenantRow);
  _deleteCancel.addEventListener("click", closeDeleteModal);
  _deleteConfirm.addEventListener("click", handleDeleteUser);

  _tenantUnsub = TenantContext.onChange(applyFilters);
  TenantContext.mountSelect(root.querySelector("#tenant-select"));

  load();
}

export function unmount(root) {
  if (_tenantUnsub) {
    _tenantUnsub();
    _tenantUnsub = null;
  }
  const tenantSelect = root.querySelector("#tenant-select");
  if (tenantSelect) TenantContext.unmountSelect(tenantSelect);
  _tableView.unbind();
  root.replaceChildren();
}

export async function load() {
  _tableView.showLoading();
  try {
    const data = await UsersService.list();
    _allUsers = data.users || [];
    applyFilters();
  } catch (e) {
    _tableView.showError(e.message);
  }
}

function applyFilters() {
  const tenantId = TenantContext.getTenantId();
  const emailQ = _emailFilter?.value.trim().toLowerCase();
  const roleQ = _roleFilter?.value;
  const statusQ = _statusFilter?.value;

  let filtered = tenantId ? _allUsers.filter((u) => u.tenantId === tenantId) : _allUsers;
  if (emailQ) filtered = filtered.filter((u) => u.email?.toLowerCase().includes(emailQ));
  if (roleQ === "pending") filtered = filtered.filter((u) => !u.groups || u.groups.length === 0);
  else if (roleQ) filtered = filtered.filter((u) => u.groups?.includes(roleQ));
  if (statusQ === "active") filtered = filtered.filter((u) => u.enabled !== false);
  else if (statusQ === "inactive") filtered = filtered.filter((u) => u.enabled === false);

  filtered = filtered.map((u) => ({ ...u, role: u.groups?.[0] || "pending" }));

  const noUsersEl = _root.querySelector("#no-users");
  noUsersEl.textContent = roleQ === "pending" ? "No pending users." : "No users found.";
  _tableView.setRows(filtered);
}

function renderRow(user) {
  const groups = user.groups || [];
  const role = user.role ?? groups[0] ?? "pending";
  const statusEl =
    groups.length > 0
      ? h("span", { className: "badge badge-success" }, "Active")
      : h("span", { className: "badge badge-neutral" }, "Pending");
  const roleBtn = iconBtn("edit", "Assign Role");
  const deleteBtn = iconBtn("discard", "Delete", "btn-icon-danger");
  const tr = h(
    "tr",
    null,
    h("td", null, user.email || "-"),
    h("td", null, statusEl),
    h("td", null, role),
    h("td", null, user.tenantId || "-"),
    h("td", null, Helpers.formatDate(user.createdAt)),
    h("td", null, h("div", { className: "row-actions" }, roleBtn, deleteBtn)),
  );
  roleBtn.addEventListener("click", () => openAssignModal(user));
  deleteBtn.addEventListener("click", () => openDeleteModal(user));
  return tr;
}

async function openAssignModal(user) {
  _pendingUsername = user.username;
  _assignRoleEmail.textContent = user.email;
  _assignRoleError.classList.add("hidden");
  _assignRoleTitle.textContent = user.groups?.length > 0 ? "Change role" : "Approve user";

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
  openModal(_assignModal);
}

function closeAssignModal() {
  closeModal(_assignModal);
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
  openModal(_deleteModal);
}

function closeDeleteModal() {
  closeModal(_deleteModal);
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
