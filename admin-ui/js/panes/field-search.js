/**
 * Field search pane — searches across all blueprint fields.
 * Results show fields with rule toggles (same as editor), grouped by doc type.
 * Editable when a tenant is selected.
 */
import * as Store from "../state/blueprint-store.js";
import * as RulesService from "../services/rules.js";
import * as TenantContext from "../utils/tenant-context.js";
import * as Toast from "../utils/toast.js";
import { h } from "../utils/dom.js";

let _root = null;
let _unsub = null;
let _input = null;
let _results = null;
let _timeout = null;
let _searchRules = {}; // { docType: { fieldName: "required"|"optional"|"excluded" } }
let _dirty = false;

export function mount(root) {
  _root = root;
  root.innerHTML = `
    <div class="nav-search">
      <input type="text" id="bp-field-search" placeholder="Search fields...">
    </div>
  `; // eslint-disable-line no-unsanitized/property -- static template

  _input = root.querySelector("#bp-field-search");
  _results = document.querySelector("#bp-search-results");

  _input.addEventListener("input", () => {
    clearTimeout(_timeout);
    _timeout = setTimeout(() => search(_input.value.trim()), 200);
  });

  _unsub = Store.subscribe(() => {});

  return unmount;
}

function unmount() {
  if (_unsub) {
    _unsub();
    _unsub = null;
  }
  if (_root) _root.replaceChildren();
}

async function loadRulesForDocType(tenantId, docType) {
  if (!tenantId) return {};
  try {
    const data = await RulesService.get(tenantId, docType);
    const rule = data.rules?.[0] || {};
    const rules = {};
    for (const f of rule.requiredFields || []) rules[f] = "required";
    for (const f of rule.optionalFields || []) rules[f] = "optional";
    return rules;
  } catch {
    return {};
  }
}

function search(query) {
  const editor = document.querySelector("#extraction-rule-editor-pane");
  const title = document.querySelector("#view-title");
  if (!query) {
    _results.innerHTML = "";
    _dirty = false;
    _searchRules = {};
    if (editor) editor.classList.remove("hidden");
    const activeNav = document.querySelector(".sidebar-nav .nav-item.active");
    if (title) title.textContent = Store.get().activeDocType || (activeNav ? activeNav.textContent.trim() : "");
    return;
  }

  const { schemas } = Store.get();
  const matches = [];

  for (const [docType, fields] of Object.entries(schemas)) {
    for (const field of fields) {
      if (field.name.toLowerCase().includes(query.toLowerCase())) {
        matches.push({ docType, field });
      }
    }
  }

  if (editor) editor.classList.add("hidden");
  Store.set({ activeDocType: null });
  if (title) title.textContent = `Search: "${query}"`;

  if (matches.length === 0) {
    _results.replaceChildren(h("p", { className: "empty-state" }, "No fields found."));
    return;
  }

  // Group by docType
  const grouped = {};
  for (const m of matches) {
    if (!grouped[m.docType]) grouped[m.docType] = [];
    grouped[m.docType].push(m.field);
  }

  renderResults(grouped);
}

async function renderResults(grouped) {
  const tenantId = TenantContext.getTenantId();
  _searchRules = {};
  _dirty = false;

  // Load rules for each doc type
  for (const docType of Object.keys(grouped)) {
    _searchRules[docType] = await loadRulesForDocType(tenantId, docType);
  }

  _results.replaceChildren();

  // Use screen-level Save/Discard buttons
  const saveBtn = document.querySelector("#bp-save-btn");
  const discardBtn = document.querySelector("#bp-discard-btn");

  if (saveBtn) {
    saveBtn.classList.remove("hidden");
    saveBtn.disabled = true;
    saveBtn.textContent = "Save Changes";
    saveBtn.onclick = async () => {
      await saveAllRules();
      saveBtn.disabled = true;
      if (discardBtn) discardBtn.classList.add("hidden");
      _dirty = false;
      Toast.show("Rules saved");
    };
  }

  if (discardBtn) {
    discardBtn.classList.add("hidden");
    discardBtn.onclick = () => {
      search(_input.value.trim());
      Toast.show("Changes discarded");
    };
  }

  function markDirty() {
    _dirty = true;
    if (saveBtn) saveBtn.disabled = false;
    if (discardBtn) discardBtn.classList.remove("hidden");
  }

  for (const [docType, fields] of Object.entries(grouped)) {
    const group = h("div", { className: "search-group" }, h("div", { className: "search-group-header" }, docType));

    for (const field of fields) {
      const fieldState = (_searchRules[docType] || {})[field.name] || "excluded";
      const radioName = `search-${docType}-${field.name}`;
      const editable = !!tenantId;

      function makeToggle(value, label, cls) {
        const input = h("input", { type: "radio", name: radioName, value });
        if (editable && fieldState === value) input.checked = true;
        if (!editable) input.disabled = true;
        input.addEventListener("change", () => {
          if (!_searchRules[docType]) _searchRules[docType] = {};
          if (value === "excluded") delete _searchRules[docType][field.name];
          else _searchRules[docType][field.name] = value;
          markDirty();
        });
        return h("label", { className: "toggle-label" }, input, h("span", { className: `toggle-badge ${cls}` }, label));
      }

      const row = h(
        "div",
        { className: "field-row" },
        h("div", { className: "field-info" }, h("span", { className: "field-name" }, field.name), h("span", { className: "field-type" }, field.type || "string")),
        h("div", { className: "field-toggles" }, makeToggle("required", "Required", "toggle-required"), makeToggle("optional", "Optional", "toggle-optional"), makeToggle("excluded", "Excluded", "toggle-excluded")),
      );
      group.appendChild(row);
    }

    _results.appendChild(group);
  }
}

async function saveAllRules() {
  const tenantId = TenantContext.getTenantId();
  if (!tenantId) return;

  for (const [docType, rules] of Object.entries(_searchRules)) {
    const requiredFields = [];
    const optionalFields = [];
    for (const [field, rule] of Object.entries(rules)) {
      if (rule === "required") requiredFields.push(field);
      else if (rule === "optional") optionalFields.push(field);
    }
    try {
      await RulesService.put(tenantId, docType, requiredFields, optionalFields);
    } catch (e) {
      Toast.show(`Failed to save ${docType}: ${e.message}`);
    }
  }
}
