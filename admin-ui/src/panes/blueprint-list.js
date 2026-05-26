/**
 * Blueprint list pane - renders document type list, dispatches selection to store.
 */
import * as Store from "../state/blueprint-store.js";
import * as Helpers from "../utils/helpers.js";

let _root = null;
let _unsub = null;

export function mount(root) {
  _root = root;
  _unsub = Store.subscribe(render);
  render(Store.get());
  return unmount;
}

function unmount() {
  if (_unsub) {
    _unsub();
    _unsub = null;
  }
  if (_root) _root.replaceChildren();
}

function render(state) {
  if (!_root) return;
  const { schemas, schemasLoading, activeDocType } = state;
  _root.innerHTML = "";

  if (schemasLoading) {
    _root.innerHTML = '<li class="empty-state">Loading…</li>';
    return;
  }

  const docTypes = Object.keys(schemas).sort();
  if (docTypes.length === 0) {
    _root.innerHTML = '<li class="empty-state">No blueprints loaded</li>';
    return;
  }

  for (const docType of docTypes) {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.className = "nav-item" + (docType === activeDocType ? " active" : "");
    a.textContent = docType;
    a.addEventListener("click", () => {
      Store.set({ activeDocType: docType, dirty: false });
    });
    li.appendChild(a);
    _root.appendChild(li);
  }
}
