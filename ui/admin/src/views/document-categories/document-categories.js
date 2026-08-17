import * as CategoriesService from "../../services/document-categories.js";
import * as TenantContext from "../../utils/tenant-context.js";
import * as Helpers from "../../utils/helpers.js";
import * as Toast from "../../utils/toast.js";
import { openModal, closeModal } from "../../utils/modal.js";
import { h, iconBtn } from "../../utils/dom.js";
import { tpl } from "../../utils/tpl.js";
import { TableView } from "../../utils/table-view.js";
import html from "./document-categories.html";

const tmpl = tpl(html);

let _root, _tableView, _createBtn, _refreshBtn, _searchInput, _sourceFilter, _rateFilter;
let _modal,
  _form,
  _tenantSelect,
  _nameInput,
  _displayNameInput,
  _descriptionInput,
  _processingPercentageInput,
  _cancelBtn,
  _errorEl,
  _titleEl;
let _deactivateModal, _deactivateName, _deactivateError, _deactivateCancel, _deactivateConfirm;
let _datesEl, _createdAtEl, _updatedAtEl;
let _editingCategory = null;
let _editingTenantId = null;
let _pendingDeactivate = null;
let _pendingDeactivateTenantId = null;
let _tenantUnsub = null;
let _allCategories = [];

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  _createBtn = h("button", { className: "btn-primary" }, "Create Category");
  _refreshBtn = h("button", { className: "btn-secondary" }, "Refresh");
  Helpers.setViewActions(_createBtn, _refreshBtn);

  _tableView = new TableView(
    root.querySelector("#categories-table"),
    root.querySelector("#categories-tbody"),
    root.querySelector("#no-categories"),
    renderRow,
  ).bindSortHeaders(root.querySelector("thead"));

  _modal = root.querySelector("#category-modal");
  _form = root.querySelector("#category-form");
  _tenantSelect = root.querySelector("#category-tenant");
  _nameInput = root.querySelector("#category-name");
  _displayNameInput = root.querySelector("#category-display-name");
  _descriptionInput = root.querySelector("#category-description");
  _processingPercentageInput = root.querySelector("#category-processing-percentage");
  _cancelBtn = root.querySelector("#category-cancel");
  _errorEl = root.querySelector("#category-form-error");
  _titleEl = root.querySelector("#category-modal-title");
  _datesEl = root.querySelector("#category-dates");
  _createdAtEl = root.querySelector("#category-created-at");
  _updatedAtEl = root.querySelector("#category-updated-at");

  _deactivateModal = root.querySelector("#category-deactivate-modal");
  _deactivateName = root.querySelector("#deactivate-category-name");
  _deactivateError = root.querySelector("#category-deactivate-error");
  _deactivateCancel = root.querySelector("#category-deactivate-cancel");
  _deactivateConfirm = root.querySelector("#category-deactivate-confirm");

  _tenantUnsub = TenantContext.onChange(() => loadCategories());
  TenantContext.mountSelect(root.querySelector("#tenant-select"));
  _searchInput = root.querySelector("#categories-search");
  _sourceFilter = root.querySelector("#categories-source-filter");
  _rateFilter = root.querySelector("#categories-rate-filter");
  _searchInput.addEventListener("input", applyFilters);
  _sourceFilter.addEventListener("change", applyFilters);
  _rateFilter.addEventListener("change", applyFilters);
  _createBtn.addEventListener("click", openCreateModal);
  _refreshBtn.addEventListener("click", () => loadCategories());
  _cancelBtn.addEventListener("click", closeEditModal);
  _form.addEventListener("submit", handleSubmit);
  _deactivateCancel.addEventListener("click", closeDeactivateModal);
  _deactivateConfirm.addEventListener("click", handleDeactivate);

  loadCategories();
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
  loadCategories();
}

async function loadCategories() {
  _tableView.showLoading();
  try {
    const resp = await CategoriesService.list(TenantContext.getTenantId());
    _allCategories = resp.categories || [];
    applyFilters();
  } catch (e) {
    _tableView.showError(e.message);
  }
}

function applyFilters() {
  const q = _searchInput?.value.trim().toLowerCase();
  const source = _sourceFilter?.value;
  const rate = _rateFilter?.value;

  let filtered = _allCategories;

  if (q) {
    filtered = filtered.filter(
      (c) =>
        c.categoryName?.toLowerCase().includes(q) ||
        c.displayName?.toLowerCase().includes(q) ||
        c.description?.toLowerCase().includes(q) ||
        c.tenantId?.toLowerCase().includes(q),
    );
  }

  if (source === "system") filtered = filtered.filter((c) => c.isAutoRegistered);
  else if (source === "manual") filtered = filtered.filter((c) => !c.isAutoRegistered);

  if (rate) {
    filtered = filtered.filter((c) => {
      const pct = Math.round((c.processingPercentage ?? 1) * 100);
      if (rate === "0") return pct === 0;
      if (rate === "100") return pct === 100;
      if (rate === "1-50") return pct >= 1 && pct <= 50;
      if (rate === "51-99") return pct >= 51 && pct <= 99;
      return true;
    });
  }

  _tableView.setRows(filtered);
}

function renderRow(cat) {
  const statusEl = cat.isActive
    ? h("span", { className: "badge badge-success" }, "Active")
    : h("span", { className: "badge badge-neutral" }, "Inactive");
  const editBtn = iconBtn("edit", "Edit");
  const actionsWrapper = h("div", { className: "row-actions" }, editBtn);
  if (cat.isActive) {
    const delBtn = iconBtn("discard", "Deactivate", "btn-icon-danger");
    delBtn.addEventListener("click", () => deactivate(cat));
    actionsWrapper.appendChild(delBtn);
  }
  const tr = h(
    "tr",
    null,
    h("td", null, cat.tenantId || "-"),
    h("td", null, cat.categoryName),
    h("td", null, cat.displayName),
    h("td", null, cat.description || "-"),
    h("td", null, String(Math.round((cat.processingPercentage ?? 1) * 100)) + "%"),
    h(
      "td",
      null,
      cat.isAutoRegistered
        ? h("span", { className: "badge badge-info" }, "System")
        : h("span", { className: "badge badge-warning" }, "Manual"),
    ),
    h("td", null, statusEl),
    h("td", null, actionsWrapper),
  );
  editBtn.addEventListener("click", () => openEditModal(cat));
  return tr;
}

function populateTenantSelect(selectedTenantId, disabled) {
  _tenantSelect.innerHTML = '<option value="">- Select tenant -</option>';
  for (const { value, label } of TenantContext.getOptions()) {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = label;
    if (value === selectedTenantId) opt.selected = true;
    _tenantSelect.appendChild(opt);
  }
  _tenantSelect.disabled = disabled;
}

function openCreateModal() {
  _editingCategory = null;
  _editingTenantId = null;
  _titleEl.textContent = "Create category";
  populateTenantSelect(TenantContext.getTenantId(), false);
  _nameInput.value = "";
  _nameInput.disabled = false;
  _displayNameInput.value = "";
  _descriptionInput.value = "";
  _processingPercentageInput.value = "100";
  _datesEl.classList.add("hidden");
  _errorEl.classList.add("hidden");
  openModal(_modal);
}

function openEditModal(cat) {
  _editingCategory = cat.categoryName;
  _editingTenantId = cat.tenantId;
  _titleEl.textContent = "Edit category";
  populateTenantSelect(cat.tenantId, true);
  _nameInput.value = cat.categoryName;
  _nameInput.disabled = true;
  _displayNameInput.value = cat.displayName;
  _descriptionInput.value = cat.description || "";
  _processingPercentageInput.value = String(Math.round((cat.processingPercentage ?? 1) * 100));
  _createdAtEl.textContent = cat.createdAt ? new Date(cat.createdAt).toLocaleString() : "-";
  _updatedAtEl.textContent = cat.updatedAt ? new Date(cat.updatedAt).toLocaleString() : "-";
  _datesEl.classList.remove("hidden");
  _errorEl.classList.add("hidden");
  openModal(_modal);
}

function closeEditModal() {
  closeModal(_modal);
  _editingCategory = null;
  _editingTenantId = null;
}

async function handleSubmit(e) {
  e.preventDefault();
  _errorEl.classList.add("hidden");

  const tenantId = _editingTenantId || _tenantSelect.value;
  const name = _nameInput.value.trim();
  const displayName = _displayNameInput.value.trim();
  const description = _descriptionInput.value.trim();
  const processingPercentage = Number(_processingPercentageInput.value) / 100;

  try {
    if (_editingCategory) {
      await CategoriesService.update(tenantId, _editingCategory, {
        displayName,
        description,
        processingPercentage,
      });
      Toast.show("Category updated");
    } else {
      await CategoriesService.create(
        tenantId,
        name,
        displayName,
        description,
        processingPercentage,
      );
      Toast.show("Category created");
    }
    closeEditModal();
    loadCategories();
  } catch (err) {
    _errorEl.textContent = err.message;
    _errorEl.classList.remove("hidden");
  }
}

function deactivate(cat) {
  _pendingDeactivate = cat.categoryName;
  _pendingDeactivateTenantId = cat.tenantId;
  _deactivateName.textContent = cat.categoryName;
  _deactivateError.classList.add("hidden");
  openModal(_deactivateModal);
}

function closeDeactivateModal() {
  closeModal(_deactivateModal);
  _pendingDeactivate = null;
  _pendingDeactivateTenantId = null;
}

async function handleDeactivate() {
  if (!_pendingDeactivate) return;
  _deactivateError.classList.add("hidden");
  try {
    await CategoriesService.remove(_pendingDeactivateTenantId, _pendingDeactivate);
    closeDeactivateModal();
    Toast.show("Category deactivated");
    loadCategories();
  } catch (e) {
    _deactivateError.textContent = e.message;
    _deactivateError.classList.remove("hidden");
  }
}
