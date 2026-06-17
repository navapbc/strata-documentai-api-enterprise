import * as CategoriesService from "../../services/document-categories.js";
import * as TenantContext from "../../utils/tenant-context.js";
import * as Helpers from "../../utils/helpers.js";
import * as Toast from "../../utils/toast.js";
import { openModal, closeModal } from "../../utils/modal.js";
import { h } from "../../utils/dom.js";
import { tpl } from "../../utils/tpl.js";
import html from "./document-categories.html";

const tmpl = tpl(html);

let _root, _tbody, _noCategories, _createBtn, _refreshBtn;
let _modal,
  _form,
  _tenantSelect,
  _nameInput,
  _displayNameInput,
  _descriptionInput,
  _cancelBtn,
  _errorEl,
  _titleEl;
let _deactivateModal, _deactivateName, _deactivateError, _deactivateCancel, _deactivateConfirm;
let _editingCategory = null;
let _editingTenantId = null;
let _pendingDeactivate = null;
let _pendingDeactivateTenantId = null;
let _tenantUnsub = null;
let _sortUnsub = null;
let _allCategories = [];
let _sortCol = null;
let _sortDir = "asc";

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  // Inject actions into shared header
  _createBtn = h("button", { className: "btn-primary" }, "Create Category");
  _refreshBtn = h("button", { className: "btn-secondary" }, "Refresh");
  Helpers.setViewActions(_createBtn, _refreshBtn);

  _tbody = root.querySelector("#categories-tbody");
  _noCategories = root.querySelector("#no-categories");
  _modal = root.querySelector("#category-modal");
  _form = root.querySelector("#category-form");
  _tenantSelect = root.querySelector("#category-tenant");
  _nameInput = root.querySelector("#category-name");
  _displayNameInput = root.querySelector("#category-display-name");
  _descriptionInput = root.querySelector("#category-description");
  _cancelBtn = root.querySelector("#category-cancel");
  _errorEl = root.querySelector("#category-form-error");
  _titleEl = root.querySelector("#category-modal-title");

  _tenantUnsub = TenantContext.onChange(() => {
    loadCategories();
  });
  _sortUnsub = Helpers.bindSortHeaders(root.querySelector("thead"), (col, dir) => {
    _sortCol = col;
    _sortDir = dir;
    renderTable(_allCategories);
  });

  _createBtn.addEventListener("click", openCreateModal);
  _refreshBtn.addEventListener("click", () => loadCategories());
  _cancelBtn.addEventListener("click", closeEditModal);
  _form.addEventListener("submit", handleSubmit);

  _deactivateModal = root.querySelector("#category-deactivate-modal");
  _deactivateName = root.querySelector("#deactivate-category-name");
  _deactivateError = root.querySelector("#category-deactivate-error");
  _deactivateCancel = root.querySelector("#category-deactivate-cancel");
  _deactivateConfirm = root.querySelector("#category-deactivate-confirm");
  _deactivateCancel.addEventListener("click", closeDeactivateModal);
  _deactivateConfirm.addEventListener("click", handleDeactivate);

  loadCategories();
}

export function unmount(root) {
  if (_tenantUnsub) {
    _tenantUnsub();
    _tenantUnsub = null;
  }
  if (_sortUnsub) {
    _sortUnsub();
    _sortUnsub = null;
  }
  root.replaceChildren();
}

export async function load() {
  const tenantId = TenantContext.getTenantId();
  loadCategories();
}

function clearTable() {
  _tbody.innerHTML = "";
  _noCategories.textContent = "No categories found.";
  _noCategories.classList.remove("hidden");
}

async function loadCategories() {
  try {
    const resp = await CategoriesService.list(TenantContext.getTenantId());
    _allCategories = resp.categories || [];
    renderTable(_allCategories);
  } catch (e) {
    Toast.show(`Failed to load categories: ${e.message}`);
  }
}

function renderTable(categories) {
  const sorted = Helpers.sortRows(categories, _sortCol, _sortDir);
  if (sorted.length === 0) {
    _tbody.innerHTML = "";
    _noCategories.classList.remove("hidden");
    return;
  }
  _noCategories.classList.add("hidden");
  _tbody.innerHTML = "";
  for (const cat of sorted) {
    const statusEl = cat.isActive
      ? h("span", { className: "badge badge-success" }, "Active")
      : h("span", { className: "badge badge-neutral" }, "Inactive");
    const editBtn = h("button", { className: "btn-sm btn-secondary" }, "Edit");
    const actionsWrapper = h("div", { className: "row-actions" }, editBtn);
    if (cat.isActive) {
      const delBtn = h("button", { className: "btn-sm btn-outline-danger" }, "Deactivate");
      delBtn.addEventListener("click", () => deactivate(cat));
      actionsWrapper.appendChild(delBtn);
    }
    const actionsCell = h("td", null, actionsWrapper);

    const tr = h(
      "tr",
      null,
      h("td", null, cat.tenantId || "-"),
      h("td", null, cat.categoryName),
      h("td", null, cat.displayName),
      h("td", null, cat.description || "-"),
      h("td", null, statusEl),
      actionsCell,
    );

    editBtn.addEventListener("click", () => openEditModal(cat));
    _tbody.appendChild(tr);
  }
}

function populateTenantSelect(selectedTenantId, disabled) {
  const globalSelect = document.querySelector("#global-tenant-select");
  _tenantSelect.innerHTML = '<option value="">- Select tenant -</option>';
  if (globalSelect) {
    for (const opt of globalSelect.options) {
      if (opt.value) {
        const newOpt = document.createElement("option");
        newOpt.value = opt.value;
        newOpt.textContent = opt.textContent;
        if (opt.value === selectedTenantId) newOpt.selected = true;
        _tenantSelect.appendChild(newOpt);
      }
    }
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

  try {
    if (_editingCategory) {
      await CategoriesService.update(tenantId, _editingCategory, { displayName, description });
      Toast.show("Category updated");
    } else {
      await CategoriesService.create(tenantId, name, displayName, description);
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
