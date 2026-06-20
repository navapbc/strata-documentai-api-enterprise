/**
 * Parse an HTML string into a reusable template.
 * Returns a function that clones the parsed DOM on each call.
 *
 * @param {string} html
 * @returns {() => DocumentFragment}
 */
export function tpl(html) {
  const t = document.createElement("template");
  t.innerHTML = html; // eslint-disable-line no-unsanitized/property -- static template string
  return () => /** @type {DocumentFragment} */ (t.content.cloneNode(true));
}
