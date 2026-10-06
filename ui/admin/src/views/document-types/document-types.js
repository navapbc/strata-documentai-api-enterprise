import * as SchemasService from "../../services/schemas.js";
import * as TenantsService from "../../services/tenants.js";
import * as TenantContext from "../../utils/tenant-context.js";
import { h } from "../../utils/dom.js";
import { tpl } from "../../utils/tpl.js";
import { TableView } from "../../utils/table-view.js";
import html from "./document-types.html";

const tmpl = tpl(html);

let _root, _tenantUnsub, _tableView;
let _searchInput;
let _allSchemas = [];
let _enabledSet = null; // null = all enabled, Set = explicit opt-in list
let _currentTenantId = null;

function humanizeCategory(cat) {
  return cat ? cat.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "—";
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
    placeholder: "— Select tenant —",
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
    _enabledSet = null;
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

    const raw = tenantResp.enabledDocumentTypes ?? tenantResp.enabled_document_types;
    _enabledSet = Array.isArray(raw) ? new Set(raw) : null;

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
  return _enabledSet === null || _enabledSet.has(documentType);
}

function renderRow(schema) {
  const enabled = isEnabled(schema.documentType);
  const checkbox = h("input", { type: "checkbox", checked: enabled, disabled: true });
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
    h("td", null, schema.description || "—"),
    h("td", null, humanizeCategory(schema.category)),
    h("td", { style: "text-align:right" }, String(schema.fieldCount ?? "—")),
    h("td", { className: "toggle-cell" }, toggle),
  );
}
