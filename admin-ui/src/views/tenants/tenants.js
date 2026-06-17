import * as TenantsService from "../../services/tenants.js";
import * as TenantContext from "../../utils/tenant-context.js";
import * as Helpers from "../../utils/helpers.js";
import { openModal, closeModal } from "../../utils/modal.js";
import * as Toast from "../../utils/toast.js";
import { h } from "../../utils/dom.js";
import { tpl } from "../../utils/tpl.js";
import html from "./tenants.html";

const tmpl = tpl(html);

let _root, _tbody, _noTenants, _createBtn, _refreshBtn, _showInactive;
let _modal, _form, _idInput, _nameInput, _contactInput, _cancelBtn, _errorEl, _titleEl;
let _deleteModal, _deleteName, _deleteError, _deleteCancel, _deleteConfirm;
let _editingTenant = null;
let _pendingDeleteId = null;
let _sortUnsub = null;
let _allTenants = [];
let _sortCol = null;
let _sortDir = "asc";

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  // Inject actions into shared header
  _showInactive = h("input", { type: "checkbox", id: "show-inactive-tenants" });
  _createBtn = h("button", { className: "btn-primary" }, "Create Tenant");
  _refreshBtn = h("button", { className: "btn-secondary" }, "Refresh");
  const label = h(
    "label",
    { className: "inline-checkbox" },
    _showInactive,
    document.createTextNode(" Show inactive"),
  );
  Helpers.setViewActions(label, _createBtn, _refreshBtn);

  _tbody = root.querySelector("#tenants-tbody");
  _noTenants = root.querySelector("#no-tenants");

  _modal = root.querySelector("#tenant-modal");
  _form = root.querySelector("#tenant-form");
  _idInput = root.querySelector("#tenant-id");
  _nameInput = root.querySelector("#tenant-name");
  _contactInput = root.querySelector("#tenant-contact");
  _cancelBtn = root.querySelector("#tenant-cancel");
  _errorEl = root.querySelector("#tenant-form-error");
  _titleEl = root.querySelector("#tenant-modal-title");

  _deleteModal = root.querySelector("#tenant-delete-modal");
  _deleteName = root.querySelector("#tenant-delete-name");
  _deleteError = root.querySelector("#tenant-delete-error");
  _deleteCancel = root.querySelector("#tenant-delete-cancel");
  _deleteConfirm = root.querySelector("#tenant-delete-confirm");

  _createBtn.addEventListener("click", openCreateModal);
  _refreshBtn.addEventListener("click", () => load());
  _showInactive.addEventListener("change", () => load());
  _cancelBtn.addEventListener("click", closeTenantModal);
  _form.addEventListener("submit", handleSubmit);
  _deleteCancel.addEventListener("click", closeDeleteModal);
  _deleteConfirm.addEventListener("click", handleDelete);

  _sortUnsub = Helpers.bindSortHeaders(root.querySelector("thead"), (col, dir) => {
    _sortCol = col;
    _sortDir = dir;
    renderTable(_allTenants);
  });

  load();
}

export function unmount(root) {
  if (_sortUnsub) {
    _sortUnsub();
    _sortUnsub = null;
  }
  root.replaceChildren();
}

export async function load() {
  Helpers.showLoading(_tbody, _noTenants);
  try {
    const includeInactive = _showInactive?.checked || false;
    const data = await TenantsService.list(!includeInactive);
    _allTenants = data.tenants || [];
    renderTable(_allTenants);
  } catch (e) {
    _tbody.innerHTML = "";
    _noTenants.textContent = e.message;
    _noTenants.classList.remove("hidden");
  }
}

function renderTable(tenants) {
  const sorted = Helpers.sortRows(tenants, _sortCol, _sortDir);
  _tbody.innerHTML = "";
  if (sorted.length === 0) {
    _noTenants.textContent = "No tenants found.";
    _noTenants.classList.remove("hidden");
    return;
  }
  _noTenants.classList.add("hidden");

  for (const t of sorted) {
    const statusEl = t.isActive
      ? h("span", { className: "badge badge-success" }, "Active")
      : h("span", { className: "badge badge-neutral" }, "Inactive");
    const editBtn = h("button", { className: "btn-sm btn-secondary" }, "Edit");
    const actionsWrapper = h("div", { className: "row-actions" }, editBtn);
    if (t.isActive) {
      const delBtn = h("button", { className: "btn-sm btn-outline-danger" }, "Deactivate");
      delBtn.addEventListener("click", () => openDeleteModal(t));
      actionsWrapper.appendChild(delBtn);
    }
    const actionsCell = h("td", null, actionsWrapper);

    const tr = h(
      "tr",
      t.isActive ? null : { className: "row-inactive" },
      h("td", null, t.tenantId),
      h("td", null, t.displayName || "-"),
      h("td", null, t.primaryContact || "-"),
      h("td", null, statusEl),
      h("td", null, Helpers.formatDate(t.createdAt)),
      actionsCell,
    );

    editBtn.addEventListener("click", () => openEditModal(t));
    _tbody.appendChild(tr);
  }
}

function openCreateModal() {
  _editingTenant = null;
  _titleEl.textContent = "Create tenant";
  _idInput.value = "";
  _idInput.disabled = false;
  _nameInput.value = "";
  _contactInput.value = "";
  _errorEl.classList.add("hidden");
  openModal(_modal);
}

function openEditModal(tenant) {
  _editingTenant = tenant.tenantId;
  _titleEl.textContent = "Edit tenant";
  _idInput.value = tenant.tenantId;
  _idInput.disabled = true;
  _nameInput.value = tenant.displayName || "";
  _contactInput.value = tenant.primaryContact || "";
  _errorEl.classList.add("hidden");
  openModal(_modal);
}

function closeTenantModal() {
  closeModal(_modal);
  _editingTenant = null;
}

async function handleSubmit(e) {
  e.preventDefault();
  _errorEl.classList.add("hidden");

  const tenantId = _idInput.value.trim();
  const displayName = _nameInput.value.trim();
  const primaryContact = _contactInput.value.trim() || null;

  try {
    if (_editingTenant) {
      await TenantsService.update(_editingTenant, { displayName, primaryContact });
      Toast.show("Tenant updated");
    } else {
      await TenantsService.create(tenantId, displayName, primaryContact);
      Toast.show("Tenant created");
      TenantContext.load();
    }
    closeTenantModal();
    load();
  } catch (err) {
    _errorEl.textContent = err.message;
    _errorEl.classList.remove("hidden");
  }
}

function openDeleteModal(tenant) {
  _pendingDeleteId = tenant.tenantId;
  _deleteName.textContent = tenant.displayName || tenant.tenantId;
  _deleteError.classList.add("hidden");
  openModal(_deleteModal);
}

function closeDeleteModal() {
  closeModal(_deleteModal);
  _pendingDeleteId = null;
}

async function handleDelete() {
  _deleteError.classList.add("hidden");
  try {
    await TenantsService.remove(_pendingDeleteId);
    closeDeleteModal();
    Toast.show("Tenant deactivated");
    load();
  } catch (err) {
    _deleteError.textContent = err.message;
    _deleteError.classList.remove("hidden");
  }
}
