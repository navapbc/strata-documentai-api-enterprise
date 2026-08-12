/**
 * Adds a manual show/hide chevron to the sticky .filter-sidebar, so its fields
 * can be collapsed on mobile/tablet to reclaim vertical space on short
 * viewports. The chevron itself lives outside the collapsing wrapper so it
 * stays reachable when collapsed. Hidden above the 1024px breakpoint, where
 * the sidebar isn't sticky and collapsing it wouldn't do anything.
 */
const CHEVRON_SVG =
  '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 9l6 6 6-6"/></svg>';

function getFilterSidebar() {
  return document.querySelector(".filter-sidebar:not(.filter-sidebar--wide)");
}

/** Call once after mounting a new view (its .filter-sidebar is a fresh element). */
export function attach() {
  const filterSidebar = getFilterSidebar();
  if (!filterSidebar) return;

  filterSidebar.classList.remove("filter-sidebar-collapsed");

  // Only the filter controls collapse. Some views (e.g. Documents) also keep
  // a results list as a direct child of .filter-sidebar - that must stay put.
  const fieldEls = filterSidebar.querySelectorAll(":scope > .metrics-timeframe, :scope > .metrics-tabs");
  if (fieldEls.length === 0) return;

  const fieldsWrap = document.createElement("div");
  fieldsWrap.className = "filter-sidebar-fields";
  filterSidebar.insertBefore(fieldsWrap, fieldEls[0]);
  fieldEls.forEach((el) => fieldsWrap.appendChild(el));

  const label = document.createElement("span");
  label.className = "filter-collapse-label";
  label.textContent = "Show Filters";
  filterSidebar.appendChild(label);

  const chevron = document.createElement("button");
  chevron.type = "button";
  chevron.className = "filter-collapse-chevron";
  chevron.setAttribute("aria-label", "Toggle filters");
  chevron.setAttribute("aria-expanded", "true");
  // eslint-disable-next-line no-unsanitized/property -- CHEVRON_SVG is a hardcoded trusted constant
  chevron.innerHTML = CHEVRON_SVG;
  chevron.addEventListener("click", () => {
    const collapsed = !filterSidebar.classList.contains("filter-sidebar-collapsed");
    filterSidebar.classList.toggle("filter-sidebar-collapsed", collapsed);
    chevron.setAttribute("aria-expanded", String(!collapsed));
  });
  filterSidebar.appendChild(chevron);
}
