import * as Helpers from "../utils/helpers.js";
import * as UsersService from "../services/users.js";
import * as TenantsService from "../services/tenants.js";

let _tbody, _noUsers, _refreshBtn, _pendingOnlyToggle;
let _assignModal, _assignForm, _assignRoleSelect, _assignTenantInput, _assignTenantHint;
let _assignTitle, _assignEmail, _assignCancel, _assignError;
let _deleteModal, _deleteEmail, _deleteCancel, _deleteConfirm, _deleteError;

let _allUsers = [];
let _editingUsername = null;
let _pendingDeleteUsername = null;

export function init() {
  _tbody = document.getElementById("users-tbody");
  _noUsers = document.getElementById("no-users");
  _refreshBtn = document.getElementById("refresh-users-btn");
  _pendingOnlyToggle = document.getElementById("show-pending-only");

  _assignModal = document.getElementById("assign-role-modal");
  _assignForm = document.getElementById("assign-role-form");
  _assignRoleSelect = document.getElementById("assign-role");
  _assignTenantInput = document.getElementById("assign-tenant");
  _assignTenantHint = document.getElementById("assign-tenant-hint");
  _assignTitle = document.getElementById("assign-role-title");
  _assignEmail = document.getElementById("assign-role-email");
  _assignCancel = document.getElementById("assign-role-cancel");
  _assignError = document.getElementById("assign-role-error");

  _deleteModal = document.getElementById("delete-user-modal");
  _deleteEmail = document.getElementById("delete-user-email");
  _deleteCancel = document.getElementById("delete-user-cancel");
  _deleteConfirm = document.getElementById("delete-user-confirm");
  _deleteError = document.getElementById("delete-user-error");

  _refreshBtn.addEventListener("click", load);
  _pendingOnlyToggle.addEventListener("change", () => render(_allUsers));

  _assignCancel.addEventListener("click", () => _assignModal.classList.add("hidden"));
  _assignForm.addEventListener("submit", handleAssignSubmit);
  _assignRoleSelect.addEventListener("change", updateTenantFieldRequirement);

  _deleteCancel.addEventListener("click", () => _deleteModal.classList.add("hidden"));
  _deleteConfirm.addEventListener("click", handleDeleteConfirm);
}

function statusLabel(user) {
  if (!user.enabled) return { text: "Disabled", className: "badge-revoked" };
  if (!user.groups || user.groups.length === 0) return { text: "Pending", className: "badge-pending" };
  return { text: "Active", className: "badge-active" };
}

function roleLabel(user) {
  if (user.groups?.includes("super-admin")) return "super-admin";
  if (user.groups?.includes("tenant-admin")) return "tenant-admin";
  return "—";
}

function render(users) {
  _tbody.innerHTML = "";
  const filtered = _pendingOnlyToggle.checked
    ? users.filter((u) => !u.groups || u.groups.length === 0)
    : users;

  if (filtered.length === 0) {
    _noUsers.textContent = _pendingOnlyToggle.checked ? "No pending users." : "No users found.";
    _noUsers.classList.remove("hidden");
    return;
  }
  _noUsers.classList.add("hidden");

  for (const user of filtered) {
    const tr = document.createElement("tr");
    const status = statusLabel(user);
    const isPending = status.text === "Pending";
    const actionCell = isPending
      ? `<button class="btn-primary btn-sm" data-action="approve">Approve</button>
         <button class="btn-danger btn-sm" data-action="delete">Delete</button>`
      : `<button class="btn-outline btn-sm" data-action="edit">Edit</button>
         <button class="btn-danger btn-sm" data-action="delete">Delete</button>`;
    tr.innerHTML = `
      <td>${Helpers.esc(user.email || user.username || "—")}</td>
      <td><span class="badge ${status.className}">${status.text}</span></td>
      <td>${Helpers.esc(roleLabel(user))}</td>
      <td>${Helpers.esc(user.tenant_id || "—")}</td>
      <td>${Helpers.formatDate(user.created_at)}</td>
      <td class="row-actions">${actionCell}</td>
    `;
    tr.querySelectorAll("button[data-action]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const action = btn.dataset.action;
        if (action === "approve" || action === "edit") openAssignModal(user, action);
        else if (action === "delete") openDeleteModal(user);
      });
    });
    _tbody.appendChild(tr);
  }
}

async function openAssignModal(user, mode) {
  _editingUsername = user.username;
  _assignEmail.textContent = user.email || user.username;
  _assignTitle.textContent = mode === "approve" ? "Approve user" : "Edit user";

  const currentRole = roleLabel(user);
  _assignRoleSelect.value = currentRole === "super-admin" ? "super-admin" : "tenant-admin";

  _assignError.classList.add("hidden");
  await populateTenantOptions(user.tenant_id);
  updateTenantFieldRequirement();
  _assignModal.classList.remove("hidden");
}

async function populateTenantOptions(selectedTenantId) {
  // Reset to just the placeholder, then refetch and append active tenants.
  _assignTenantInput.innerHTML = '<option value="">— Select a tenant —</option>';
  try {
    const data = await TenantsService.list(true);
    for (const tenant of data.tenants || []) {
      const option = document.createElement("option");
      option.value = tenant.tenantId;
      option.textContent = `${tenant.displayName} (${tenant.tenantId})`;
      _assignTenantInput.appendChild(option);
    }
    // If the user already has a tenant that's no longer in the active list,
    // surface it explicitly so the admin sees the mismatch.
    if (selectedTenantId && ![..._assignTenantInput.options].some((o) => o.value === selectedTenantId)) {
      const option = document.createElement("option");
      option.value = selectedTenantId;
      option.textContent = `${selectedTenantId} (inactive or unknown)`;
      _assignTenantInput.appendChild(option);
    }
    if (selectedTenantId) _assignTenantInput.value = selectedTenantId;
  } catch (err) {
    console.error("Failed to load tenants for assign modal:", err);
  }
}

function updateTenantFieldRequirement() {
  const role = _assignRoleSelect.value;
  const isTenantAdmin = role === "tenant-admin";
  const row = document.getElementById("assign-tenant-row");
  if (row) row.classList.toggle("hidden", !isTenantAdmin);
  _assignTenantInput.required = isTenantAdmin;
  if (!isTenantAdmin) _assignTenantInput.value = "";
}

async function handleAssignSubmit(e) {
  e.preventDefault();
  if (!_editingUsername) return;
  _assignError.classList.add("hidden");

  const role = _assignRoleSelect.value;
  const tenantId = (_assignTenantInput.value || "").trim() || null;

  if (role === "tenant-admin" && !tenantId) {
    _assignError.textContent = "Tenant is required for tenant-admin.";
    _assignError.classList.remove("hidden");
    return;
  }

  try {
    await UsersService.approve(_editingUsername, role, tenantId);
    _assignModal.classList.add("hidden");
    _editingUsername = null;
    await load();
  } catch (err) {
    _assignError.textContent = err.message;
    _assignError.classList.remove("hidden");
  }
}

function openDeleteModal(user) {
  _pendingDeleteUsername = user.username;
  _deleteEmail.textContent = user.email || user.username;
  _deleteError.classList.add("hidden");
  _deleteModal.classList.remove("hidden");
}

async function handleDeleteConfirm() {
  if (!_pendingDeleteUsername) return;
  _deleteError.classList.add("hidden");
  const username = _pendingDeleteUsername;
  try {
    await UsersService.remove(username);
    _deleteModal.classList.add("hidden");
    _pendingDeleteUsername = null;
    await load();
  } catch (err) {
    _deleteError.textContent = err.message;
    _deleteError.classList.remove("hidden");
  }
}

export async function load() {
  try {
    const data = await UsersService.list();
    _allUsers = data.users || [];
    render(_allUsers);
  } catch (e) {
    _tbody.innerHTML = "";
    _noUsers.textContent = e.message;
    _noUsers.classList.remove("hidden");
  }
}
