/**
 * Shared document viewer components.
 * Renders preview with bbox overlay and extracted fields table.
 */

import { mergeOverlappingBoxes } from "../utils/bbox.js";
import { h } from "../utils/dom.js";

const TYPE_COLORS = {
  string: "#44aaff",
  number: "#ff8c00",
  integer: "#ff8c00",
  date: "#ffaa00",
  boolean: "#aa44ff",
  currency: "#44cc44",
  array: "#ff44aa",
  object: "#ff44aa",
  unknown: "#ff4444",
  merged: "#888888",
};

/**
 * Extract geometry data from fields response.
 * @param {Object} fields - API response fields object
 * @returns {Object|null} - map of fieldName → { geometry, fieldType }
 */
export function extractGeometry(fields) {
  const geo = {};
  for (const [key, val] of Object.entries(fields || {})) {
    if (val && typeof val === "object" && Array.isArray(val.geometry) && val.geometry.length) {
      geo[key] = { geometry: val.geometry, fieldType: val.fieldType || "unknown" };
    }
  }
  return Object.keys(geo).length ? geo : null;
}

/**
 * Render bbox overlay on top of a preview image.
 * @param {HTMLElement} container - element containing the preview image
 * @param {Object} fieldGeometry - output of extractGeometry()
 * @param {object} [options]
 * @param {number} [options.page=1] - which page to render boxes for
 * @returns {ResizeObserver|null} - observer to disconnect on cleanup
 */
export function renderBboxOverlay(container, fieldGeometry, { page = 1 } = {}) {
  clearBboxOverlay(container);
  if (!fieldGeometry) return null;

  const img = container.querySelector("img");
  if (!img) return null;

  let resizeObserver = null;

  const doRender = () => {
    clearBboxOverlay(container);
    const wrap = document.createElement("div");
    wrap.className = "bbox-overlay-wrap";
    wrap.style.width = img.offsetWidth + "px";
    wrap.style.height = img.offsetHeight + "px";
    wrap.style.top = img.offsetTop + "px";
    wrap.style.left = img.offsetLeft + "px";

    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.classList.add("bbox-overlay");
    svg.setAttribute("viewBox", "0 0 1 1");
    svg.setAttribute("preserveAspectRatio", "none");

    const tooltip = document.createElement("div");
    tooltip.className = "bbox-tooltip";
    tooltip.style.display = "none";

    const boxes = [];
    for (const [fieldName, { geometry: geoList, fieldType }] of Object.entries(fieldGeometry)) {
      for (const geo of geoList) {
        if (!geo.boundingBox) continue;
        if (geo.page && geo.page !== page) continue;
        const { left, top, width, height } = geo.boundingBox;
        boxes.push({ left, top, width, height, fieldName, fieldType });
      }
    }

    const merged = mergeOverlappingBoxes(boxes);

    for (const box of merged) {
      const color =
        box.fields.length > 1
          ? TYPE_COLORS.merged
          : TYPE_COLORS[box.fields[0].fieldType] || TYPE_COLORS.unknown;
      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", box.left);
      rect.setAttribute("y", box.top);
      rect.setAttribute("width", box.width);
      rect.setAttribute("height", box.height);
      rect.setAttribute("fill", "none");
      rect.setAttribute("stroke", color);
      rect.setAttribute("stroke-width", "0.003");
      rect.dataset.field = box.fields.map((f) => `${f.fieldName} (${f.fieldType})`).join("\n");
      svg.appendChild(rect);
    }

    svg.addEventListener("mouseenter", handleTooltip);
    svg.addEventListener("mousemove", handleTooltip);
    svg.addEventListener("mouseleave", () => {
      tooltip.style.display = "none";
    });

    function handleTooltip(e) {
      const rect = e.target.closest("rect");
      if (!rect) {
        tooltip.style.display = "none";
        return;
      }
      // eslint-disable-next-line no-unsanitized/property -- field names from server
      tooltip.innerHTML = rect.dataset.field.replace(/\n/g, "<br>");
      tooltip.style.display = "block";
      const wrapRect = wrap.getBoundingClientRect();
      tooltip.style.left = e.clientX - wrapRect.left + 8 + "px";
      tooltip.style.top = e.clientY - wrapRect.top - 24 + "px";
    }

    wrap.appendChild(svg);
    wrap.appendChild(tooltip);
    container.appendChild(wrap);
  };

  if (img.complete && img.naturalWidth) {
    doRender();
  } else {
    img.addEventListener("load", doRender, { once: true });
  }

  resizeObserver = new ResizeObserver(() => {
    if (container.querySelector("img")) doRender();
  });
  resizeObserver.observe(container);

  return resizeObserver;
}

/**
 * Remove any existing bbox overlay from a container.
 * @param {HTMLElement} container
 */
export function clearBboxOverlay(container) {
  const existing = container.querySelector(".bbox-overlay-wrap");
  if (existing) existing.remove();
}

/**
 * Render extracted fields table.
 * @param {HTMLElement} container - element to render into
 * @param {Object} fields - API response fields object
 */
export function renderFieldsTable(container, fields) {
  container.replaceChildren();

  if (!fields || !Object.keys(fields).length) {
    container.appendChild(h("p", { className: "empty-state" }, "No fields extracted"));
    return;
  }

  const tbody = h("tbody", null);
  for (const [name, data] of Object.entries(fields)) {
    const value = data?.value != null ? String(data.value) : "-";
    const conf = data?.confidence != null ? `${(data.confidence * 100).toFixed(0)}%` : "-";
    const cls =
      data?.confidence >= 0.9
        ? "confidence-high"
        : data?.confidence >= 0.7
          ? "confidence-med"
          : "confidence-low";
    tbody.appendChild(
      h("tr", null, h("td", null, name), h("td", null, value), h("td", { className: cls }, conf)),
    );
  }

  container.appendChild(
    h(
      "table",
      { className: "detail-table" },
      h(
        "thead",
        null,
        h("tr", null, h("th", null, "Field"), h("th", null, "Value"), h("th", null, "Conf.")),
      ),
      tbody,
    ),
  );
}
