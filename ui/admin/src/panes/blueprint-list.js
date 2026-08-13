/**
 * Blueprint list pane - combobox for selecting a document type.
 */
import * as Store from "../state/blueprint-store.js";
import { createCombobox } from "../utils/combobox.js";

let _root = null;
let _unsub = null;
let _combobox = null;

export function mount(root) {
  _root = root;
  _combobox = createCombobox(root, {
    placeholder: "Choose type…",
    onSelect(docType) {
      Store.set({ activeDocType: docType, dirty: false });
      const base = location.hash.split("/")[0];
      location.hash = `${base}/${docType}`;
      const mainArea = document.querySelector("#bp-main-area");
      if (mainArea) mainArea.scrollTop = 0;
    },
  });

  _unsub = Store.subscribe(render);
  render(Store.get());
  return unmount;
}

function unmount() {
  if (_unsub) {
    _unsub();
    _unsub = null;
  }
  if (_combobox) {
    _combobox.destroy();
    _combobox = null;
  }
  if (_root) _root.replaceChildren();
}

function render(state) {
  if (!_combobox) return;
  const { schemas, activeDocType } = state;
  const docTypes = Object.keys(schemas).sort();
  _combobox.setItems(docTypes);
  if (activeDocType !== null) _combobox.setValue(activeDocType || "");
}
