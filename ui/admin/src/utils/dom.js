export { h, text } from "../../../shared/utils/dom.js";
import * as Icons from "./icons.js";

/**
 * Create a btn-icon button containing an SVG icon.
 * @param {keyof typeof Icons} name
 * @param {string} title - tooltip / aria-label
 * @param {string} [extraClass]
 * @returns {HTMLButtonElement}
 */
export function iconBtn(name, title, extraClass = "") {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = ("btn-icon " + extraClass).trim();
  btn.title = title;
  btn.setAttribute("aria-label", title);
  // eslint-disable-next-line no-unsanitized/property -- Icons values are hardcoded trusted constants
  btn.innerHTML = Icons[name];
  return btn;
}
