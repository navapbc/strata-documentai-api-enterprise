/**
 * Blueprints screen — composes blueprint-list, blueprint-editor, and field-search panes.
 * Shared state lives in js/state/blueprint-store.js.
 */
import * as Store from "../state/blueprint-store.js";
import * as SchemasService from "../services/schemas.js";
import * as BlueprintList from "../panes/blueprint-list.js";
import * as ExtractionRuleEditor from "../panes/extraction-rule-editor.js";
import * as FieldSearch from "../panes/field-search.js";
import * as Toast from "../utils/toast.js";
import { h } from "../utils/dom.js";
import { setViewActions } from "../utils/helpers.js";
import { tpl } from "../utils/tpl.js";
import html from "./extraction-rules.html";

const tmpl = tpl(html);

let _unsubs = [];

export function mount(root) {
  root.replaceChildren(tmpl());

  // Inject Save/Discard into shared header
  const saveBtn = h("button", { className: "btn-primary hidden", id: "bp-save-btn" }, "Save Rules");
  const discardBtn = h("button", { className: "btn-secondary hidden", id: "bp-discard-btn" }, "Discard");
  setViewActions(discardBtn, saveBtn);

  _unsubs = [
    BlueprintList.mount(root.querySelector("#bp-list-pane")),
    ExtractionRuleEditor.mount(root.querySelector("#extraction-rule-editor-pane")),
    FieldSearch.mount(root.querySelector("#bp-search-pane")),
    Store.subscribe((state) => {
      const title = document.querySelector("#view-title");
      if (title) {
        const activeNav = document.querySelector(".sidebar-nav .nav-item.active");
        title.textContent = state.activeDocType
          ? state.activeDocType
          : (activeNav ? activeNav.textContent.trim() : "");
      }
    }),
  ];

  loadSchemas();
}

export function unmount(root) {
  _unsubs.forEach((u) => u && u());
  _unsubs = [];
  Store.reset();
  root.replaceChildren();
}

export function mountTestView(root) {
  // Test documents is a separate screen — import and mount it
  import("./test-documents.js").then((mod) => mod.mount(root));
}

export function hasUnsavedChanges() {
  return Store.get().dirty;
}

export function getActiveDocType() {
  return Store.get().activeDocType;
}

export function clearTestHistory() {
  // No-op — test history lives in test-documents view
}

async function loadSchemas() {
  try {
    const data = await SchemasService.getAllFields();
    const schemas = {};
    for (const field of data.fields || []) {
      const docType = field.documentType;
      if (!schemas[docType]) schemas[docType] = [];
      schemas[docType].push(field);
    }
    Store.set({ schemas, schemasLoading: false });
  } catch (e) {
    Store.set({ schemasLoading: false });
    Toast.show(`Failed to load schemas: ${e.message}`);
  }
}

// Re-export for sidebar population (used by main.js dashboard setup)
export function populateSidebar() {
  // No-op — the list pane auto-renders from store subscription
}

export function select(docType) {
  Store.set({ activeDocType: docType });
}

export async function load() {
  await loadSchemas();
}
