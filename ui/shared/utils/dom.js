/**
 * Create a DOM element with attributes and children.
 * Text children become text nodes (auto-escaped by the browser).
 * Element children are appended directly.
 *
 * @param {string} tag
 * @param {Object<string, string>|null} attrs
 * @param {...(string|Node)} children
 * @returns {HTMLElement}
 */
export function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  if (attrs) {
    for (const [key, val] of Object.entries(attrs)) {
      if (key === "className") el.className = val;
      else if (key.startsWith("data-")) el.setAttribute(key, val);
      else el.setAttribute(key, val);
    }
  }
  for (const child of children) {
    if (child == null) continue;
    if (typeof child === "string")
      el.appendChild(document.createTextNode(child));
    else el.appendChild(child);
  }
  return el;
}

/**
 * Create a text node.
 * @param {string} text
 * @returns {Text}
 */
export function text(text) {
  return document.createTextNode(text ?? "");
}
