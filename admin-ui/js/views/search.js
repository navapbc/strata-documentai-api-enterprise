import * as Helpers from "../utils/helpers.js";
import * as Toast from "../utils/toast.js";
import * as BlueprintsView from "./blueprints.js";
import { DEMO_SCHEMAS } from "../demo/schemas.js";
import { DEMO_RULES } from "../demo/rules.js";

let _results, _title, _saveBtn, _discardBtn, _searchInput, _isDemo = false;
let _timeout = null;
let _dirty = false;
let _lastQuery = "";
let _onNavigate = null;

export function init({ results, title, saveBtn, discardBtn, searchInput, onNavigate }) {
  _results = results;
  _title = title;
  _saveBtn = saveBtn;
  _discardBtn = discardBtn;
  _searchInput = searchInput;
  _onNavigate = onNavigate;

  _searchInput.addEventListener("input", () => {
    clearTimeout(_timeout);
    _timeout = setTimeout(() => search(_searchInput.value.trim()), 200);
  });

  _searchInput.addEventListener("focus", () => {
    if (_lastQuery && _searchInput.value.trim()) {
      if (_onNavigate) _onNavigate("view-search");
    }
  });

  _saveBtn.addEventListener("click", saveChanges);
  _discardBtn.addEventListener("click", () => {
    search(_lastQuery);
    Toast.show("Changes discarded");
  });
}

export function setDemo(val) { _isDemo = val; }
export function isDirty() { return _dirty; }

function markDirty() {
  if (!_dirty) {
    _dirty = true;
    _saveBtn.disabled = false;
    _discardBtn.classList.remove("hidden");
  }
}

function markClean() {
  _dirty = false;
  _saveBtn.disabled = true;
  _discardBtn.classList.add("hidden");
}

function search(query) {
  _lastQuery = query;
  markClean();

  if (!query) {
    const active = BlueprintsView.getActiveDocType();
    if (active) BlueprintsView.select(active);
    else if (_onNavigate) _onNavigate("view-empty");
    return;
  }

  const schemas = _isDemo ? DEMO_SCHEMAS : {};
  const results = {};

  for (const [docType, fields] of Object.entries(schemas)) {
    const matches = fields.filter((f) => f.name.toLowerCase().includes(query.toLowerCase()));
    if (matches.length > 0) results[docType] = matches;
  }

  _title.textContent = `Search: "${query}"`;
  _results.innerHTML = "";

  if (Object.keys(results).length === 0) {
    _results.innerHTML = '<p class="empty-state">No fields found.</p>';
    if (_onNavigate) _onNavigate("view-search");
    return;
  }

  for (const [docType, fields] of Object.entries(results)) {
    const rules = _isDemo ? (DEMO_RULES[docType] || {}) : {};
    const required = new Set(rules.requiredFields || []);
    const optional = new Set(rules.optionalFields || []);

    const group = document.createElement("div");
    group.className = "search-group";
    group.innerHTML = `<div class="search-group-header">${Helpers.esc(docType)}</div>`;

    for (const field of fields) {
      let state = "excluded";
      if (required.has(field.name)) state = "required";
      else if (optional.has(field.name)) state = "optional";

      const row = document.createElement("div");
      row.className = "field-row";
      row.innerHTML = `
        <div class="field-info">
          <span class="field-name">${Helpers.esc(field.name)}</span>
          <span class="field-type">${Helpers.esc(field.type)}</span>
        </div>
        <div class="field-toggles">
          <label class="toggle-label">
            <input type="radio" name="search-${Helpers.esc(docType)}-${Helpers.esc(field.name)}" value="required" ${state === "required" ? "checked" : ""}>
            <span class="toggle-badge toggle-required">Required</span>
          </label>
          <label class="toggle-label">
            <input type="radio" name="search-${Helpers.esc(docType)}-${Helpers.esc(field.name)}" value="optional" ${state === "optional" ? "checked" : ""}>
            <span class="toggle-badge toggle-optional">Optional</span>
          </label>
          <label class="toggle-label">
            <input type="radio" name="search-${Helpers.esc(docType)}-${Helpers.esc(field.name)}" value="excluded" ${state === "excluded" ? "checked" : ""}>
            <span class="toggle-badge toggle-excluded">Excluded</span>
          </label>
        </div>
      `;
      row.querySelectorAll("input").forEach((input) => {
        input.addEventListener("change", markDirty);
      });
      group.appendChild(row);
    }

    _results.appendChild(group);
  }

  if (_onNavigate) _onNavigate("view-search");
}

function saveChanges() {
  _results.querySelectorAll(".search-group").forEach((group) => {
    const docType = group.querySelector(".search-group-header").textContent;
    const rules = _isDemo ? (DEMO_RULES[docType] || { requiredFields: [], optionalFields: [] }) : {};
    const required = new Set(rules.requiredFields || []);
    const optional = new Set(rules.optionalFields || []);

    group.querySelectorAll(".field-row").forEach((row) => {
      const name = row.querySelector(".field-name").textContent;
      const checked = row.querySelector("input:checked");
      required.delete(name);
      optional.delete(name);
      if (checked?.value === "required") required.add(name);
      else if (checked?.value === "optional") optional.add(name);
    });

    if (_isDemo) {
      DEMO_RULES[docType] = {
        requiredFields: [...required],
        optionalFields: [...optional],
      };
    }
  });

  markClean();
  BlueprintsView.populateSidebar(DEMO_SCHEMAS);
  Toast.show("Changes saved");
}
