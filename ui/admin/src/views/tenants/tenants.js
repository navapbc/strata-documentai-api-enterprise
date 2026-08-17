import * as TenantsService from "../../services/tenants.js";
import * as TenantContext from "../../utils/tenant-context.js";
import * as Helpers from "../../utils/helpers.js";
import { openModal, closeModal } from "../../utils/modal.js";
import * as Toast from "../../utils/toast.js";
import { h, iconBtn } from "../../utils/dom.js";
import { tpl } from "../../utils/tpl.js";
import { TableView } from "../../utils/table-view.js";
import html from "./tenants.html";

const tmpl = tpl(html);

let _root, _tableView, _createBtn;
let _showInactive;
let _modal,
  _form,
  _idInput,
  _nameInput,
  _contactInput,
  _maxPerDayInput,
  _maxPerMonthInput,
  _confidenceFloorInput,
  _cancelBtn,
  _errorEl,
  _titleEl;
let _deleteModal, _deleteName, _deleteError, _deleteCancel, _deleteConfirm;
let _editingTenant = null;
let _pendingDeleteId = null;
let _allTenants = [];

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  _showInactive = h("input", { type: "checkbox", id: "show-inactive-tenants" });
  _createBtn = h("button", { className: "btn-primary" }, "Create Tenant");
  const label = h(
    "label",
    { className: "inline-checkbox" },
    _showInactive,
    document.createTextNode(" Show inactive"),
  );
  Helpers.setViewActions(label, _createBtn);

  _tableView = new TableView(
    root.querySelector("#tenants-table"),
    root.querySelector("#tenants-tbody"),
    root.querySelector("#no-tenants"),
    renderRow,
  );

  _modal = root.querySelector("#tenant-modal");
  _form = root.querySelector("#tenant-form");
  _idInput = root.querySelector("#tenant-id");
  _nameInput = root.querySelector("#tenant-name");
  _contactInput = root.querySelector("#tenant-contact");
  _maxPerDayInput = root.querySelector("#tenant-max-writes-per-day");
  _maxPerMonthInput = root.querySelector("#tenant-max-writes-per-month");
  _confidenceFloorInput = root.querySelector("#tenant-confidence-floor");
  _cancelBtn = root.querySelector("#tenant-cancel");
  _errorEl = root.querySelector("#tenant-form-error");
  _titleEl = root.querySelector("#tenant-modal-title");

  _deleteModal = root.querySelector("#tenant-delete-modal");
  _deleteName = root.querySelector("#tenant-delete-name");
  _deleteError = root.querySelector("#tenant-delete-error");
  _deleteCancel = root.querySelector("#tenant-delete-cancel");
  _deleteConfirm = root.querySelector("#tenant-delete-confirm");

  _createBtn.addEventListener("click", openCreateModal);
  _showInactive.addEventListener("change", () => load());
  _cancelBtn.addEventListener("click", closeTenantModal);
  _form.addEventListener("submit", handleSubmit);
  _deleteCancel.addEventListener("click", closeDeleteModal);
  _deleteConfirm.addEventListener("click", handleDelete);

  _tableView.bindSortHeaders(root.querySelector("thead"));

  load();
}

export function unmount(root) {
  _tableView.unbind();
  root.replaceChildren();
}

export async function load() {
  _tableView.showLoading();
  try {
    const includeInactive = _showInactive?.checked || false;
    const data = await TenantsService.list(!includeInactive);
    _allTenants = data.tenants || [];
    _tableView.setRows(_allTenants);
  } catch (e) {
    _tableView.showError(e.message);
  }
}

function renderRow(t) {
  const statusEl = t.isActive
    ? h("span", { className: "badge badge-success" }, "Active")
    : h("span", { className: "badge badge-neutral" }, "Inactive");
  const editBtn = iconBtn("edit", "Edit");
  const actionsWrapper = h("div", { className: "row-actions" }, editBtn);
  if (t.isActive) {
    const delBtn = iconBtn("discard", "Deactivate", "btn-icon-danger");
    delBtn.addEventListener("click", () => openDeleteModal(t));
    actionsWrapper.appendChild(delBtn);
  }
  const tr = h(
    "tr",
    t.isActive ? null : { className: "row-inactive" },
    h("td", null, t.tenantId),
    h("td", null, t.displayName || "-"),
    h(
      "td",
      null,
      t.extractionConfidenceFloor != null
        ? `${Math.round(t.extractionConfidenceFloor * 100)}%`
        : "-",
    ),
    h("td", null, t.maxWritesPerDay != null ? String(t.maxWritesPerDay) : "-"),
    h("td", null, t.maxWritesPerMonth != null ? String(t.maxWritesPerMonth) : "-"),
    h("td", null, statusEl),
    h("td", null, actionsWrapper),
  );
  editBtn.addEventListener("click", () => openEditModal(t));
  return tr;
}

function openCreateModal() {
  _editingTenant = null;
  _titleEl.textContent = "Create tenant";
  _idInput.value = "";
  _idInput.disabled = false;
  _nameInput.value = "";
  _contactInput.value = "";
  _maxPerDayInput.value = "";
  _maxPerMonthInput.value = "";
  _confidenceFloorInput.value = "";
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
  _maxPerDayInput.value = tenant.maxWritesPerDay ?? "";
  _maxPerMonthInput.value = tenant.maxWritesPerMonth ?? "";
  _confidenceFloorInput.value =
    tenant.extractionConfidenceFloor != null
      ? Math.round(tenant.extractionConfidenceFloor * 100)
      : "";
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
  const maxWritesPerDay = _maxPerDayInput.value ? parseInt(_maxPerDayInput.value, 10) : null;
  const maxWritesPerMonth = _maxPerMonthInput.value ? parseInt(_maxPerMonthInput.value, 10) : null;
  const confidenceFloor = _confidenceFloorInput.value
    ? parseFloat(_confidenceFloorInput.value) / 100
    : null;

  try {
    if (_editingTenant) {
      await TenantsService.update(_editingTenant, {
        displayName,
        primaryContact,
        maxWritesPerDay,
        maxWritesPerMonth,
        extractionConfidenceFloor: confidenceFloor,
      });
      Toast.show("Tenant updated");
    } else {
      await TenantsService.create(
        tenantId,
        displayName,
        primaryContact,
        maxWritesPerDay,
        maxWritesPerMonth,
        confidenceFloor,
      );
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
