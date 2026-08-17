import * as DocumentsService from "../../services/documents.js";
import * as Helpers from "../../utils/helpers.js";
import * as Toast from "../../utils/toast.js";
import * as TenantContext from "../../utils/tenant-context.js";
import * as DateRangePicker from "../../utils/date-range-picker.js";
import * as CategoriesService from "../../services/document-categories.js";
import * as SchemasService from "../../services/schemas.js";
import { createCombobox } from "../../utils/combobox.js";
import { tpl } from "../../utils/tpl.js";
import { mount as mountViewerPane } from "../../panes/document-viewer-pane.js";
import html from "./document-search.html";

const tmpl = tpl(html);

let _root, _listEl, _noDocuments, _resultsTab, _tenantMsg;
let _filenameInput,
  _docTypeInput,
  _blueprintCombobox,
  _blueprintValue = "";
let _datePicker = null;
let _searchBtn, _clearBtn, _loadMoreBtn;
let _tabFilters, _tabResults;
let _unsubTenant = null;
let _searchResults = [];
let _nextCursor = null;
let _pane = null;
let _filterMain = null;
let _savedState = null;

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  Helpers.setViewActions();

  _filenameInput = root.querySelector("#doc-search-filename");
  _docTypeInput = root.querySelector("#doc-search-doc-type");
  _blueprintCombobox = createCombobox(root.querySelector("#doc-search-blueprint"), {
    placeholder: "Any type...",
    onSelect(val) {
      _blueprintValue = val;
    },
  });
  _datePicker = DateRangePicker.mount(root.querySelector("#doc-search-date-range"));
  _searchBtn = root.querySelector("#doc-search-btn");
  _clearBtn = root.querySelector("#doc-search-clear-btn");
  _listEl = root.querySelector("#documents-list");
  _noDocuments = root.querySelector("#no-documents");
  _loadMoreBtn = root.querySelector("#doc-search-load-more");

  loadBlueprints();
  _tabFilters = root.querySelector("#doc-search-tab-filters");
  _tabResults = root.querySelector("#doc-search-tab-results");
  _resultsTab = root.querySelector(".sidebar-tab[data-tab='results']");
  _tenantMsg = root.querySelector("#doc-search-tenant-msg");

  _pane = mountViewerPane(root.querySelector("#doc-viewer-pane"));
  _filterMain = root.querySelector(".filter-main");
  _pane.hide();
  _filterMain.style.display = "none";

  root.querySelectorAll(".sidebar-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      root.querySelectorAll(".sidebar-tab").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      _tabFilters.classList.toggle("hidden", btn.dataset.tab !== "filters");
      _tabResults.classList.toggle("hidden", btn.dataset.tab !== "results");
      _filterMain.style.display =
        btn.dataset.tab === "results" ? "" : _pane.hasSelection() ? "" : "none";
    });
  });

  TenantContext.mountSelect(root.querySelector("#tenant-select"), { placeholder: "Select Tenant" });
  _unsubTenant = TenantContext.onChange(() => {
    _tenantMsg.classList.add("hidden");
    loadCategories();
    resetResults();
  });

  if (_savedState) {
    const s = _savedState;
    _filenameInput.value = s.filename;
    _blueprintValue = s.blueprintValue;
    _docTypeInput.value = s.docType;
    _searchResults = s.results;
    _nextCursor = s.nextCursor;
    _resultsTab.textContent = `Results (${_searchResults.length}${_nextCursor ? "+" : ""})`;
    _resultsTab.disabled = false;
    _pane.show(_listEl, _searchResults, { autoSelect: false });
    _loadMoreBtn.classList.toggle("hidden", !_nextCursor);
    if (s.activeTab === "results") {
      _resultsTab.click();
    }
  }

  _searchBtn.addEventListener("click", () => {
    if (!TenantContext.getTenantId()) {
      _tenantMsg.classList.remove("hidden");
      return;
    }
    if (!validateDates()) return;
    resetResults();
    runSearch();
  });

  _loadMoreBtn.addEventListener("click", () => runSearch({ append: true }));

  _clearBtn.addEventListener("click", () => {
    _filenameInput.value = "";
    _datePicker.reset();
    _docTypeInput.value = "";
    _blueprintCombobox.setValue("");
    _blueprintValue = "";
    _tenantMsg.classList.add("hidden");
    resetResults();
  });

  [_filenameInput].forEach((el) => {
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        if (!TenantContext.getTenantId()) {
          _tenantMsg.classList.remove("hidden");
          return;
        }
        if (!validateDates()) return;
        resetResults();
        runSearch();
      }
    });
  });
}

export function unmount(root) {
  if (_searchResults.length) {
    _savedState = {
      results: _searchResults,
      nextCursor: _nextCursor,
      filename: _filenameInput?.value ?? "",
      blueprintValue: _blueprintValue,
      docType: _docTypeInput?.value ?? "",
      activeTab: root.querySelector(".sidebar-tab.active")?.dataset.tab ?? "filters",
    };
  } else {
    _savedState = null;
  }
  if (_pane) {
    _pane.unmount();
    _pane = null;
  }
  if (_blueprintCombobox) {
    _blueprintCombobox.destroy();
    _blueprintCombobox = null;
  }
  if (_unsubTenant) {
    _unsubTenant();
    _unsubTenant = null;
  }
  const tenantSelect = root.querySelector("#tenant-select");
  if (tenantSelect) TenantContext.unmountSelect(tenantSelect);
  root.replaceChildren();
}

function validateDates() {
  const { dateFrom, dateTo } = _datePicker.getRange();
  if (dateFrom && dateTo && dateFrom > dateTo) {
    Toast.show("Date From cannot be after Date To.");
    return false;
  }
  return true;
}

// Blueprints are currently global (shared across all tenants).
// If per-tenant blueprints are introduced, load based on selected tenant instead.
async function loadBlueprints() {
  try {
    const resp = await SchemasService.list();
    _blueprintCombobox.setItems(resp.schemas || []);
  } catch {
    /* leave empty */
  }
}

async function loadCategories() {
  const tenantId = TenantContext.getTenantId();
  _docTypeInput.innerHTML = '<option value="">Any</option>';
  if (!tenantId) return;
  try {
    const resp = await CategoriesService.list(tenantId);
    const current = _docTypeInput.value;
    (resp.categories || []).forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.categoryName;
      opt.textContent = c.categoryName;
      _docTypeInput.appendChild(opt);
    });
    _docTypeInput.value = current;
  } catch {
    /* leave as Any */
  }
}

function resetResults() {
  _searchResults = [];
  _nextCursor = null;
  _listEl.innerHTML = "";
  _noDocuments.classList.add("hidden");
  _loadMoreBtn.classList.add("hidden");
  _resultsTab.textContent = "Results";
  _resultsTab.disabled = true;
  _resultsTab.classList.remove("active");
  _root.querySelector(".sidebar-tab[data-tab='filters']").classList.add("active");
  _tabFilters.classList.remove("hidden");
  _tabResults.classList.add("hidden");
  _pane.hide();
  _filterMain.style.display = "none";
}

async function runSearch({ append = false } = {}) {
  _noDocuments.textContent = append ? "Loading…" : "Searching…";
  _noDocuments.classList.remove("hidden");
  _loadMoreBtn.disabled = true;
  _searchBtn.disabled = true;

  try {
    const { dateFrom, dateTo } = _datePicker.getRange();
    const resp = await DocumentsService.search({
      tenantId: TenantContext.getTenantId() || undefined,
      filename: _filenameInput.value.trim() || undefined,
      dateFrom: dateFrom || undefined,
      dateTo: dateTo || undefined,
      userProvidedDocumentType: _docTypeInput.value || undefined,
      matchedBlueprintName: _blueprintValue || undefined,
      limit: 50,
      cursor: append ? _nextCursor : undefined,
    });

    const docs = resp.documents ?? [];
    _nextCursor = resp.nextCursor ?? null;

    if (append) {
      _searchResults.push(...docs);
      _pane.append(_listEl, docs);
    } else {
      _searchResults = docs;
      if (!_searchResults.length) {
        _noDocuments.textContent = "No documents found.";
        _noDocuments.classList.remove("hidden");
      } else {
        _noDocuments.classList.add("hidden");
        _pane.clear();
        _pane.show(_listEl, _searchResults, { autoSelect: false });
      }
    }

    if (append) _noDocuments.classList.add("hidden");

    _loadMoreBtn.classList.toggle("hidden", !_nextCursor);
    _resultsTab.textContent = `Results (${_searchResults.length}${_nextCursor ? "+" : ""})`;
    _resultsTab.disabled = false;
    _resultsTab.click();
  } catch (e) {
    Toast.show(`Search failed: ${e.message}`);
    _noDocuments.textContent = "Search failed.";
    _noDocuments.classList.remove("hidden");
  } finally {
    _searchBtn.disabled = false;
    _loadMoreBtn.disabled = false;
  }
}
