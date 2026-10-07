import * as SchemasService from "../../services/schemas.js";
import * as TenantsService from "../../services/tenants.js";
import * as TenantContext from "../../utils/tenant-context.js";
import { h } from "../../utils/dom.js";
import { tpl } from "../../utils/tpl.js";
import { TableView } from "../../utils/table-view.js";
import * as Toast from "../../utils/toast.js";
import html from "./blueprints.html";

const tmpl = tpl(html);

let _root, _tenantUnsub, _tableView;
let _searchInput;
let _allSchemas = [];
let _disabledSet = null; // null = none disabled, Set = disabled document types
let _currentTenantId = null;

function humanizeCategory(cat) {
  return cat ? cat.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "-";
}

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  _searchInput = root.querySelector("#blueprints-search");

  _tableView = new TableView(
    root.querySelector("#blueprints-table"),
    root.querySelector("#blueprints-tbody"),
    root.querySelector("#no-blueprints"),
    renderRow,
  ).bindSortHeaders(root.querySelector("thead"));

  TenantContext.mountSelect(root.querySelector("#tenant-select"), {
    placeholder: "- Select tenant -",
  });
  _tenantUnsub = TenantContext.onChange((tenantId) => {
    _currentTenantId = tenantId;
    load();
  });

  _searchInput.addEventListener("input", applyFilters);

  _currentTenantId = TenantContext.getTenantId();
  load();
}

export function unmount(root) {
  _tableView.unbind();
  if (_tenantUnsub) {
    _tenantUnsub();
    _tenantUnsub = null;
  }
  const sel = root.querySelector("#tenant-select");
  if (sel) TenantContext.unmountSelect(sel);
  root.replaceChildren();
}

async function load() {
  _tableView.showLoading();

  if (!_currentTenantId) {
    _disabledSet = null;
    try {
      const schemasResp = await SchemasService.list();
      _allSchemas = schemasResp.schemas || [];
      _root.querySelector("#blueprints-table").classList.add("no-tenant");
      applyFilters();
    } catch (e) {
      _tableView.showError(e.message);
    }
    return;
  }

  _root.querySelector("#blueprints-table").classList.remove("no-tenant");

  try {
    const [schemasResp, tenantResp] = await Promise.all([
      SchemasService.list(),
      TenantsService.get(_currentTenantId),
    ]);

    _allSchemas = schemasResp.schemas || [];

    const raw = tenantResp.disabledBlueprintList ?? tenantResp.disabled_blueprint_list;
    _disabledSet = Array.isArray(raw) ? new Set(raw) : null;

    applyFilters();
  } catch (e) {
    _tableView.showError(e.message);
  }
}

function applyFilters() {
  const q = _searchInput?.value.trim().toLowerCase();
  const filtered = q
    ? _allSchemas.filter(
        (s) =>
          s.documentType.toLowerCase().includes(q) ||
          s.description?.toLowerCase().includes(q) ||
          s.category?.toLowerCase().includes(q),
      )
    : _allSchemas;
  _tableView.setRows(filtered);
}

function isEnabled(documentType) {
  return _disabledSet === null || !_disabledSet.has(documentType);
}

async function handleToggle(documentType, enabled, checkbox) {
  if (!_currentTenantId) return;

  if (!enabled) {
    _disabledSet = _disabledSet
      ? new Set([..._disabledSet, documentType])
      : new Set([documentType]);
  } else {
    _disabledSet?.delete(documentType);
  }

  const row = checkbox.closest("tr");
  const toggleCell = row?.cells[row.cells.length - 1];
  const toggleEl = toggleCell?.firstChild;
  if (toggleCell) toggleCell.replaceChildren(h("div", { className: "toggle-spinner" }));
  if (row) {
    row.classList.remove("saved");
    void row.offsetWidth;
    row.classList.add("saved");
  }

  try {
    await Promise.all([
      TenantsService.update(_currentTenantId, {
        disabledBlueprintList: _disabledSet && _disabledSet.size > 0 ? [..._disabledSet] : [],
      }),
      new Promise((r) => setTimeout(r, 500)),
    ]);
  } catch (e) {
    // Revert on failure
    if (!enabled) {
      _disabledSet?.delete(documentType);
    } else {
      _disabledSet = _disabledSet
        ? new Set([..._disabledSet, documentType])
        : new Set([documentType]);
    }
    Toast.show(e.message);
    _tableView.setRows([..._allSchemas]);
  } finally {
    if (toggleCell && toggleEl) toggleCell.replaceChildren(toggleEl);
  }
}

function renderRow(schema) {
  const enabled = isEnabled(schema.documentType);
  const checkbox = h("input", { type: "checkbox" });
  checkbox.checked = enabled;
  checkbox.addEventListener("change", () =>
    handleToggle(schema.documentType, checkbox.checked, checkbox),
  );
  const toggle = h(
    "label",
    { className: "toggle-switch" },
    checkbox,
    h("span", { className: "toggle-track" }),
  );

  return h(
    "tr",
    null,
    h("td", null, schema.documentType),
    h("td", null, schema.description || "-"),
    h("td", null, humanizeCategory(schema.category)),
    h("td", { style: "text-align:right" }, String(schema.fieldCount ?? "-")),
    h("td", { className: "toggle-cell" }, toggle),
  );
}
