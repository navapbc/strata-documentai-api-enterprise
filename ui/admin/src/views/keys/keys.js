import * as Helpers from "../../utils/helpers.js";
import * as KeysService from "../../services/keys.js";
import * as TenantContext from "../../utils/tenant-context.js";
import { openModal, closeModal } from "../../utils/modal.js";
import { h } from "../../utils/dom.js";
import { tpl } from "../../utils/tpl.js";
import * as Toast from "../../utils/toast.js";
import html from "./keys.html";

const tmpl = tpl(html);

let _root, _tbody, _noKeys, _createKeyBtn;
let _createModal, _createForm, _cancelCreate;
let _keyCreatedModal, _newKeyValue, _copyKeyBtn, _closeCreated;
let _refreshKeysBtn;
let _revokeModal, _revokeKeyPrefix, _cancelRevoke, _confirmRevoke;
let _pendingRevokeKey = null;
let _showInactiveToggle;
let _tenantUnsub = null;
let _sortUnsub = null;
let _allKeys = [];
let _sortCol = null;
let _sortDir = "asc";

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  // Inject actions into shared header
  _showInactiveToggle = h("input", { type: "checkbox", id: "show-inactive-keys" });
  _createKeyBtn = h("button", { className: "btn-primary" }, "Create Key");
  _refreshKeysBtn = h("button", { className: "btn-secondary" }, "Refresh");
  const label = h(
    "label",
    { className: "inline-checkbox" },
    _showInactiveToggle,
    document.createTextNode(" Show revoked"),
  );
  Helpers.setViewActions(label, _createKeyBtn, _refreshKeysBtn);

  _tbody = root.querySelector("#keys-tbody");
  _noKeys = root.querySelector("#no-keys");
  _createModal = root.querySelector("#create-modal");
  _createForm = root.querySelector("#create-form");
  _cancelCreate = root.querySelector("#cancel-create");
  _keyCreatedModal = root.querySelector("#key-created-modal");
  _newKeyValue = root.querySelector("#new-key-value");
  _copyKeyBtn = root.querySelector("#copy-key-btn");
  _closeCreated = root.querySelector("#close-created");
  _revokeModal = root.querySelector("#revoke-modal");
  _revokeKeyPrefix = root.querySelector("#revoke-key-prefix");
  _cancelRevoke = root.querySelector("#cancel-revoke");
  _confirmRevoke = root.querySelector("#confirm-revoke");

  _createKeyBtn.addEventListener("click", openCreateModal);
  _cancelCreate.addEventListener("click", () => closeModal(_createModal));
  _createForm.addEventListener("submit", handleCreate);
  _copyKeyBtn.addEventListener("click", copyKey);
  _closeCreated.addEventListener("click", () => closeModal(_keyCreatedModal));
  _refreshKeysBtn.addEventListener("click", () => load());
  _cancelRevoke.addEventListener("click", closeRevokeModal);
  _confirmRevoke.addEventListener("click", handleConfirmRevoke);

  if (_showInactiveToggle) {
    _showInactiveToggle.addEventListener("change", () => load());
  }

  _tenantUnsub = TenantContext.onChange(() => load());
  _sortUnsub = Helpers.bindSortHeaders(root.querySelector("thead"), (col, dir) => {
    _sortCol = col;
    _sortDir = dir;
    renderTable(_allKeys);
  });
  load();
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

function openRevokeModal(key) {
  _pendingRevokeKey = key.keyPrefix;
  _revokeKeyPrefix.textContent = key.keyPrefix;
  const nameEl = _revokeModal.querySelector("#revoke-key-name");
  const tenantEl = _revokeModal.querySelector("#revoke-key-tenant");
  const envEl = _revokeModal.querySelector("#revoke-key-env");
  if (nameEl) nameEl.textContent = key.apiKeyName || "-";
  if (tenantEl) tenantEl.textContent = key.tenantId || "-";
  if (envEl) envEl.textContent = key.environment || "-";
  openModal(_revokeModal);
}

function closeRevokeModal() {
  _pendingRevokeKey = null;
  closeModal(_revokeModal);
}

async function handleConfirmRevoke() {
  if (!_pendingRevokeKey) return;
  const keyPrefix = _pendingRevokeKey;
  closeRevokeModal();
  try {
    await KeysService.revoke(keyPrefix);
    Toast.show("API key revoked");
    await load();
  } catch (e) {
    Toast.show(`Failed to revoke: ${e.message}`);
  }
}

function openCreateModal() {
  openModal(_createModal);
  const tenantSelect = _root.querySelector("#key-tenant");
  /** @type {HTMLSelectElement} */
  const globalSelect = document.querySelector("#global-tenant-select");
  tenantSelect.innerHTML = '<option value="">\u2014 Select tenant \u2014</option>';
  if (globalSelect) {
    for (const opt of globalSelect.options) {
      if (opt.value) {
        const newOpt = document.createElement("option");
        newOpt.value = opt.value;
        newOpt.textContent = opt.textContent;
        tenantSelect.appendChild(newOpt);
      }
    }
  }
  _root.querySelector("#api-key-name").value = "";
  _root.querySelector("#client-environment").value = "dev";
  _root.querySelector("#client-email").value = "";
}

async function handleCreate(e) {
  e.preventDefault();
  const tenantId = _root.querySelector("#key-tenant").value.trim();
  const apiKeyName = _root.querySelector("#api-key-name").value.trim();
  const environment = _root.querySelector("#client-environment").value.trim() || "dev";
  const emailAddress = _root.querySelector("#client-email").value.trim() || undefined;
  try {
    const result = await KeysService.create(
      apiKeyName,
      environment,
      undefined,
      emailAddress,
      tenantId,
    );
    closeModal(_createModal);
    _newKeyValue.textContent = result.apiKey || "-";
    openModal(_keyCreatedModal);
    Toast.show("API key created");
    await load();
  } catch (err) {
    Toast.show(`Failed to create key: ${err.message}`);
  }
}

function copyKey() {
  navigator.clipboard.writeText(_newKeyValue.textContent);
  _copyKeyBtn.textContent = "Copied!";
  setTimeout(() => (_copyKeyBtn.textContent = "Copy"), 2000);
}

export function render(keys) {
  return renderTable(keys);
}

function renderTable(keys) {
  const sorted = Helpers.sortRows(keys, _sortCol, _sortDir);
  _tbody.innerHTML = "";
  if (sorted.length === 0) {
    _noKeys.textContent = "No API keys found.";
    _noKeys.classList.remove("hidden");
    return;
  }
  _noKeys.classList.add("hidden");
  for (const key of sorted) {
    const isActive = key.isActive !== false;
    const actionEl = isActive
      ? h("button", { className: "btn-outline-danger btn-sm" }, "Revoke")
      : h("span", { className: "badge badge-revoked" }, "Revoked");
    const tr = h(
      "tr",
      isActive ? null : { className: "row-inactive" },
      h("td", null, key.tenantId || "-"),
      h("td", null, key.apiKeyName || "-"),
      h("td", null, key.emailAddress || "-"),
      h("td", null, key.environment || "-"),
      h("td", null, h("code", null, key.keyPrefix ? key.keyPrefix + "…" : "-")),
      h("td", null, Helpers.formatDate(key.createdAt)),
      h("td", null, key.lastUsed ? Helpers.formatDate(key.lastUsed) : "-"),
      h("td", null, actionEl),
    );
    if (isActive) {
      actionEl.addEventListener("click", () => openRevokeModal(key));
    }
    _tbody.appendChild(tr);
  }
}

export async function load() {
  Helpers.showLoading(_tbody, _noKeys);
  try {
    const includeInactive = _showInactiveToggle?.checked || false;
    const tenantId = TenantContext.getTenantId();
    const data = await KeysService.list({ includeInactive, tenantId });
    _allKeys = data.keys || [];
    renderTable(_allKeys);
  } catch (e) {
    _tbody.innerHTML = "";
    _noKeys.textContent = e.message;
    _noKeys.classList.remove("hidden");
  }
}
