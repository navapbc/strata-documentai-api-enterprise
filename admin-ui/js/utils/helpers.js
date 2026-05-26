export function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString();
}

export function esc(str) {
  const el = document.createElement("span");
  el.textContent = str || "";
  return el.innerHTML;
}

export function showLoading(tbody, emptyEl) {
  tbody.innerHTML = "";
  if (emptyEl) {
    emptyEl.textContent = "Loading…";
    emptyEl.classList.remove("hidden");
  }
}


/**
 * Inject action elements into the shared #view-actions container.
 * Clears previous actions first.
 * @param  {...Node} elements
 */
export function setViewActions(...elements) {
  const container = document.querySelector("#view-actions");
  if (!container) return;
  container.replaceChildren(...elements);
}

/**
 * Clear the shared #view-actions container.
 */
export function clearViewActions() {
  const container = document.querySelector("#view-actions");
  if (container) container.replaceChildren();
}
