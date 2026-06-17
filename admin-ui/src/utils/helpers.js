export function formatDate(iso) {
  if (!iso) return "-";
  return new Date(iso).toLocaleDateString();
}

export function formatDateTime(iso) {
  if (!iso) return "-";
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function esc(str) {
  const el = document.createElement("span");
  el.textContent = str || "";
  return el.innerHTML;
}

export function showLoading(tbody, emptyEl) {
  if (emptyEl) emptyEl.classList.add("hidden");
  tbody.innerHTML =
    '<tr><td colspan="99" style="text-align:center;color:#9ca3af;padding:2rem;font-style:italic;">Loading…</td></tr>';
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

/**
 * Sort an array by a direct property key.
 * Uses locale-aware, numeric-aware string comparison so ISO dates and numbers sort correctly.
 * @param {any[]} rows
 * @param {string|null} col - property key to sort by; pass null to skip sorting
 * @param {'asc'|'desc'} dir
 */
export function sortRows(rows, col, dir = "asc") {
  if (!col) return rows;
  return [...rows].sort((a, b) => {
    const av = a[col] ?? "";
    const bv = b[col] ?? "";
    const cmp = String(av).localeCompare(String(bv), undefined, {
      numeric: true,
      sensitivity: "base",
    });
    return dir === "desc" ? -cmp : cmp;
  });
}

/**
 * Attach click-to-sort behaviour to all th[data-col] elements inside thead.
 * Marks the active column with th-sort-asc / th-sort-desc classes.
 * Calls onChange(col, dir) whenever the sort changes.
 * Returns a cleanup function.
 * @param {HTMLTableSectionElement} thead
 * @param {(col: string, dir: 'asc'|'desc') => void} onChange
 */
export function bindSortHeaders(thead, onChange) {
  thead.querySelectorAll("th[data-col]").forEach((th) => th.classList.add("th-sortable"));
  function handleClick(e) {
    const th = e.target.closest("th[data-col]");
    if (!th) return;
    const wasAsc = th.classList.contains("th-sort-asc");
    const dir = wasAsc ? "desc" : "asc";
    thead
      .querySelectorAll("th[data-col]")
      .forEach((t) => t.classList.remove("th-sort-asc", "th-sort-desc"));
    th.classList.add(dir === "asc" ? "th-sort-asc" : "th-sort-desc");
    onChange(th.dataset.col, dir);
  }
  thead.addEventListener("click", handleClick);
  return () => thead.removeEventListener("click", handleClick);
}
