import * as DocumentsService from "../../services/documents.js";
import * as Helpers from "../../utils/helpers.js";
import * as TenantContext from "../../utils/tenant-context.js";
import { tpl } from "../../utils/tpl.js";
import { mount as mountViewerPane } from "../../panes/document-viewer-pane.js";
import html from "./documents.html";

const tmpl = tpl(html);

const STORAGE_KEY_ACTIVE = "docai_documents_active_job";
const STORAGE_KEY_LIMIT = "docai_documents_limit";

let _listEl, _noDocuments;
let _statusFilter, _limitFilter;
let _unsubTenant = null;
let _recentDocuments = [];
let _pane = null;

export function mount(root) {
  root.replaceChildren(tmpl());

  Helpers.setViewActions();

  _recentDocuments = [];

  _statusFilter = root.querySelector("#document-status-filter");
  _limitFilter = root.querySelector("#document-limit-filter");
  _listEl = root.querySelector("#documents-list");
  _noDocuments = root.querySelector("#no-documents");

  _pane = mountViewerPane(root.querySelector("#doc-viewer-pane"));
  _pane.hide();

  const savedLimit = sessionStorage.getItem(STORAGE_KEY_LIMIT);
  if (savedLimit) _limitFilter.value = savedLimit;

  _statusFilter.addEventListener("change", () => load());
  _limitFilter.addEventListener("change", () => {
    sessionStorage.setItem(STORAGE_KEY_LIMIT, _limitFilter.value);
    sessionStorage.removeItem(STORAGE_KEY_ACTIVE);
    load();
  });

  TenantContext.mountSelect(root.querySelector("#tenant-select"), { placeholder: "Select Tenant" });
  _unsubTenant = TenantContext.onChange(() => {
    sessionStorage.removeItem(STORAGE_KEY_ACTIVE);
    _pane.hide();
    load();
  });

  load();
}

export function unmount(root) {
  if (_pane) {
    _pane.unmount();
    _pane = null;
  }
  if (_unsubTenant) {
    _unsubTenant();
    _unsubTenant = null;
  }
  const tenantSelect = root.querySelector("#tenant-select");
  if (tenantSelect) TenantContext.unmountSelect(tenantSelect);
  root.replaceChildren();
}

export async function load() {
  const tenantId = TenantContext.getTenantId() || undefined;

  if (!tenantId) {
    _recentDocuments = [];
    _listEl.innerHTML = "";
    _pane.clear();
    _pane.hide();
    showNoDocuments("Select a tenant to view recent documents");
    return;
  }

  const status = _statusFilter?.value || undefined;
  const limit = parseInt(_limitFilter.value, 10);

  try {
    const resp = await DocumentsService.list({ tenantId, status, limit });
    _recentDocuments = resp.documents || resp || [];
  } catch {
    _recentDocuments = [];
  }

  if (!_recentDocuments.length) {
    _listEl.innerHTML = "";
    _pane.hide();
    showNoDocuments("No documents found");
    return;
  }

  hideNoDocuments();
  _pane.clear();
  _pane.show(_listEl, _recentDocuments, { autoSelect: false });

  const savedActive = sessionStorage.getItem(STORAGE_KEY_ACTIVE);
  const firstJobId = savedActive || _recentDocuments[0].jobId;
  sessionStorage.setItem(STORAGE_KEY_ACTIVE, firstJobId);
  _pane.select(_listEl, firstJobId);
}

function showNoDocuments(msg) {
  _noDocuments.textContent = msg;
  _noDocuments.classList.remove("hidden");
}

function hideNoDocuments() {
  _noDocuments.classList.add("hidden");
}
