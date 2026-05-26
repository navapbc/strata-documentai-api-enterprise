/**
 * Blueprint store — shared state for the blueprints screen.
 *
 * Panes subscribe to state changes. No pane imports another directly.
 */

const _listeners = new Set();

let _state = {
  schemas: {}, // { docType: [{ name, type }, ...] }
  schemasLoading: true, // true until initial load completes
  activeDocType: null, // currently selected document type
  rules: {}, // { fieldName: "required"|"optional"|"excluded" }
  dirty: false, // unsaved changes in editor
  tenantId: null, // selected tenant for rules
};

export function get() {
  return _state;
}

export function set(patch) {
  _state = { ..._state, ...patch };
  _listeners.forEach((fn) => fn(_state));
}

export function subscribe(fn) {
  _listeners.add(fn);
  return () => _listeners.delete(fn);
}

export function reset() {
  _state = {
    schemas: {},
    schemasLoading: true,
    activeDocType: null,
    rules: {},
    dirty: false,
    tenantId: null,
  };
}
