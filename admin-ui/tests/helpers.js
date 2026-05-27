/**
 * Test DOM helpers - encapsulate common dispatch patterns.
 */

export function typeInto(el, value) {
  el.value = value;
  el.dispatchEvent(new Event("input"));
}

export function changeValue(el, value) {
  el.value = value;
  el.dispatchEvent(new Event("change"));
}

export function flush() {
  return new Promise((r) => setTimeout(r, 0));
}
