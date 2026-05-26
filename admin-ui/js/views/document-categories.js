import * as CategoriesService from "../services/document-categories.js";
import * as TenantContext from "../utils/tenant-context.js";
import * as Helpers from "../utils/helpers.js";
import * as Toast from "../utils/toast.js";
import { h } from "../utils/dom.js";
import { tpl } from "../utils/tpl.js";
import html from "./document-categories.html";

const tmpl = tpl(html);

let _root, _tbody, _noCategories, _createBtn, _refreshBtn;
let _modal, _form, _nameInput, _displayNameInput, _descriptionInput, _cancelBtn, _errorEl, _titleEl;
let _editingCategory = null;
let _tenantUnsub = null;

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  // Inject actions into shared header
  _createBtn = h("button", { className: "btn-primary", disabled: "true" }, "+ Create Category");
  _refreshBtn = h("button", { className: "btn-secondary" }, "Refresh");
  Helpers.setViewActions(_createBtn, _refreshBtn);

  _tbody = root.querySelector("#categories-tbody");
  _noCategories = root.querySelector("#no-categories");
  _modal = root.querySelector("#category-modal");
  _form = root.querySelector("#category-form");
  _nameInput = root.querySelector("#category-name");
  _displayNameInput = root.querySelector("#category-display-name");
  _descriptionInput = root.querySelector("#category-description");
  _cancelBtn = root.querySelector("#category-cancel");
  _errorEl = root.querySelector("#category-form-error");
  _titleEl = root.querySelector("#category-modal-title");

  const tenantId = TenantContext.getTenantId();
  _createBtn.disabled = !tenantId;

  _tenantUnsub = TenantContext.onChange((tid) => {
    _createBtn.disabled = !tid;
    loadCategories();
  });

  _createBtn.addEventListener("click", openCreateModal);
  _refreshBtn.addEventListener("click", () => {
    if (TenantContext.getTenantId()) loadCategories();
  });
  _cancelBtn.addEventListener("click", closeModal);
  _form.addEventListener("submit", handleSubmit);

  loadCategories();
}

export function unmount(root) {
  if (_tenantUnsub) {
    _tenantUnsub();
    _tenantUnsub = null;
  }
  root.replaceChildren();
}

export async function load() {
  const tenantId = TenantContext.getTenantId();
  loadCategories();
}

function clearTable() {
  _tbody.innerHTML = "";
  _noCategories.classList.remove("hidden");
}

async function loadCategories() {
  try {
    const resp = await CategoriesService.list(TenantContext.getTenantId());
    renderTable(resp.categories || []);
  } catch (e) {
    Toast.show(`Failed to load categories: ${e.message}`);
  }
}

function renderTable(categories) {
  if (categories.length === 0) {
    _tbody.innerHTML = "";
    _noCategories.classList.remove("hidden");
    return;
  }
  _noCategories.classList.add("hidden");
  _tbody.innerHTML = "";
  for (const cat of categories) {
    const statusEl = cat.isActive
      ? h("span", { className: "badge badge-success" }, "Active")
      : h("span", { className: "badge badge-neutral" }, "Inactive");
    const editBtn = h("button", { className: "btn-sm btn-secondary" }, "Edit");
    const actionsCell = h("td", null, editBtn);
    if (cat.isActive) {
      const delBtn = h("button", { className: "btn-sm btn-danger" }, "Deactivate");
      delBtn.addEventListener("click", () => deactivate(cat.categoryName));
      actionsCell.appendChild(delBtn);
    }

    const tr = h(
      "tr",
      null,
      h("td", null, cat.tenantId || "—"),
      h("td", null, cat.categoryName),
      h("td", null, cat.displayName),
      h("td", null, cat.description || "—"),
      h("td", null, statusEl),
      actionsCell,
    );

    editBtn.addEventListener("click", () =>
      openEditModal(cat.categoryName, cat.displayName, cat.description || ""),
    );
    _tbody.appendChild(tr);
  }
}

function openCreateModal() {
  _editingCategory = null;
  _titleEl.textContent = "Create category";
  _nameInput.value = "";
  _nameInput.disabled = false;
  _displayNameInput.value = "";
  _descriptionInput.value = "";
  _errorEl.classList.add("hidden");
  _modal.classList.remove("hidden");
}

function openEditModal(name, displayName, description) {
  _editingCategory = name;
  _titleEl.textContent = "Edit category";
  _nameInput.value = name;
  _nameInput.disabled = true;
  _displayNameInput.value = displayName;
  _descriptionInput.value = description;
  _errorEl.classList.add("hidden");
  _modal.classList.remove("hidden");
}

function closeModal() {
  _modal.classList.add("hidden");
  _editingCategory = null;
}

async function handleSubmit(e) {
  e.preventDefault();
  _errorEl.classList.add("hidden");

  const name = _nameInput.value.trim();
  const displayName = _displayNameInput.value.trim();
  const description = _descriptionInput.value.trim();

  try {
    if (_editingCategory) {
      await CategoriesService.update(TenantContext.getTenantId(), _editingCategory, {
        displayName,
        description,
      });
      Toast.show("Category updated");
    } else {
      await CategoriesService.create(TenantContext.getTenantId(), name, displayName, description);
      Toast.show("Category created");
    }
    closeModal();
    loadCategories();
  } catch (err) {
    _errorEl.textContent = err.message;
    _errorEl.classList.remove("hidden");
  }
}

function deactivate(categoryName) {
  if (!confirm(`Deactivate category "${categoryName}"?`)) return;

  CategoriesService.remove(TenantContext.getTenantId(), categoryName)
    .then(() => {
      Toast.show("Category deactivated");
      loadCategories();
    })
    .catch((e) => Toast.show(`Failed: ${e.message}`));
}
