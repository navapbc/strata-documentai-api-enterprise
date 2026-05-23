import * as Helpers from "../utils/helpers.js";
import * as TenantsService from "../services/tenants.js";

let _tbody, _noTenants, _refreshBtn, _showInactiveToggle, _createBtn;
let _modal, _form, _modalTitle, _idInput, _nameInput, _contactInput, _cancelBtn, _formError;
let _deleteModal, _deleteName, _deleteCancel, _deleteConfirm, _deleteError;

let _allTenants = [];
let _editingId = null; // null = create mode
let _pendingDeleteId = null;
let _tenantsLoadedListeners = [];

export function init() {
  _tbody = document.getElementById("tenants-tbody");
  _noTenants = document.getElementById("no-tenants");
  _refreshBtn = document.getElementById("refresh-tenants-btn");
  _showInactiveToggle = document.getElementById("show-inactive-tenants");
  _createBtn = document.getElementById("create-tenant-btn");

  _modal = document.getElementById("tenant-modal");
  _form = document.getElementById("tenant-form");
  _modalTitle = document.getElementById("tenant-modal-title");
  _idInput = document.getElementById("tenant-id");
  _nameInput = document.getElementById("tenant-name");
  _contactInput = document.getElementById("tenant-contact");
  _cancelBtn = document.getElementById("tenant-cancel");
  _formError = document.getElementById("tenant-form-error");

  _deleteModal = document.getElementById("tenant-delete-modal");
  _deleteName = document.getElementById("tenant-delete-name");
  _deleteCancel = document.getElementById("tenant-delete-cancel");
  _deleteConfirm = document.getElementById("tenant-delete-confirm");
  _deleteError = document.getElementById("tenant-delete-error");

  _refreshBtn.addEventListener("click", load);
  _showInactiveToggle.addEventListener("change", load);
  _createBtn.addEventListener("click", openCreateModal);
  _cancelBtn.addEventListener("click", () => _modal.classList.add("hidden"));
  _form.addEventListener("submit", handleSubmit);
  _deleteCancel.addEventListener("click", () => _deleteModal.classList.add("hidden"));
  _deleteConfirm.addEventListener("click", handleDeleteConfirm);
}

export function getTenants() { return _allTenants; }

export function onTenantsLoaded(cb) {
  _tenantsLoadedListeners.push(cb);
}

function render(tenants) {
  _tbody.innerHTML = "";
  if (tenants.length === 0) {
    _noTenants.textContent = _showInactiveToggle.checked
      ? "No tenants found."
      : "No active tenants. Click \"+ Create Tenant\" to add one.";
    _noTenants.classList.remove("hidden");
    return;
  }
  _noTenants.classList.add("hidden");

  for (const tenant of tenants) {
    const tr = document.createElement("tr");
    const status = tenant.isActive
      ? '<span class="badge badge-active">Active</span>'
      : '<span class="badge badge-revoked">Inactive</span>';
    if (!tenant.isActive) tr.classList.add("row-inactive");
    tr.innerHTML = `
      <td><code>${Helpers.esc(tenant.tenantId)}</code></td>
      <td>${Helpers.esc(tenant.displayName)}</td>
      <td>${Helpers.esc(tenant.primaryContact || "—")}</td>
      <td>${status}</td>
      <td>${Helpers.formatDate(tenant.createdAt)}</td>
      <td class="row-actions">
        <button class="btn-outline btn-sm" data-action="edit">Edit</button>
        <button class="btn-danger btn-sm" data-action="delete" ${tenant.isActive ? "" : "disabled"}>Delete</button>
      </td>
    `;
    tr.querySelectorAll("button[data-action]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const action = btn.dataset.action;
        if (action === "edit") openEditModal(tenant);
        else if (action === "delete") openDeleteModal(tenant);
      });
    });
    _tbody.appendChild(tr);
  }
}

function openCreateModal() {
  _editingId = null;
  _modalTitle.textContent = "Create tenant";
  _idInput.value = "";
  _idInput.disabled = false;
  _nameInput.value = "";
  _contactInput.value = "";
  _formError.classList.add("hidden");
  _modal.classList.remove("hidden");
}

function openEditModal(tenant) {
  _editingId = tenant.tenantId;
  _modalTitle.textContent = "Edit tenant";
  _idInput.value = tenant.tenantId;
  _idInput.disabled = true; // ID is the hash key, cannot change
  _nameInput.value = tenant.displayName;
  _contactInput.value = tenant.primaryContact || "";
  _formError.classList.add("hidden");
  _modal.classList.remove("hidden");
}

async function handleSubmit(e) {
  e.preventDefault();
  _formError.classList.add("hidden");

  const tenantId = _idInput.value.trim();
  const displayName = _nameInput.value.trim();
  const primaryContact = _contactInput.value.trim() || null;

  try {
    if (_editingId) {
      await TenantsService.update(_editingId, { displayName, primaryContact });
    } else {
      await TenantsService.create(tenantId, displayName, primaryContact);
    }
    _modal.classList.add("hidden");
    _editingId = null;
    await load();
  } catch (err) {
    _formError.textContent = err.message;
    _formError.classList.remove("hidden");
  }
}

function openDeleteModal(tenant) {
  _pendingDeleteId = tenant.tenantId;
  _deleteName.textContent = `${tenant.displayName} (${tenant.tenantId})`;
  _deleteError.classList.add("hidden");
  _deleteModal.classList.remove("hidden");
}

async function handleDeleteConfirm() {
  if (!_pendingDeleteId) return;
  _deleteError.classList.add("hidden");
  const id = _pendingDeleteId;
  try {
    await TenantsService.remove(id);
    _deleteModal.classList.add("hidden");
    _pendingDeleteId = null;
    await load();
  } catch (err) {
    _deleteError.textContent = err.message;
    _deleteError.classList.remove("hidden");
  }
}

export async function load() {
  try {
    const activeOnly = !_showInactiveToggle.checked;
    const data = await TenantsService.list(activeOnly);
    _allTenants = data.tenants || [];
    render(_allTenants);
    _tenantsLoadedListeners.forEach((cb) => cb(_allTenants));
  } catch (e) {
    _tbody.innerHTML = "";
    _noTenants.textContent = e.message;
    _noTenants.classList.remove("hidden");
  }
}
