/**
 * Shared document viewer components.
 * Renders preview with bbox overlay and extracted fields table.
 */

import { mergeOverlappingBoxes } from "../utils/bbox.js";
import { esc } from "../utils/helpers.js";
import { h } from "../utils/dom.js";

export const PREVIEWABLE_TYPES = ["application/pdf", "image/jpeg", "image/png"];

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
 * Does this entry carry a field payload (a leaf), vs. being a group of nested
 * fields? The presentation layer nests dotted field names (e.g. `employer.address`)
 * into a tree, so a group is a plain object whose members are themselves entries.
 * A scalar, an array, or an object bearing the field shape (value/confidence/
 * geometry) is a leaf.
 * @param {*} val
 * @returns {boolean}
 */
function isLeafField(val) {
  if (val == null || typeof val !== "object" || Array.isArray(val)) return true;
  return "value" in val || "confidence" in val || "geometry" in val;
}

/**
 * Flatten a nested fields tree back to a flat map of dot-joined names → leaf.
 * The viewer (table rows, geometry, hover-linking) keys everything on a flat
 * field name, while the API nests the `fields` block for presentation; this
 * bridges the two and yields the canonical dotted name as the key.
 * @param {Object} fields - API response fields object (possibly nested)
 * @param {string} [prefix] - accumulated dotted prefix (internal)
 * @param {Object} [out] - accumulator (internal)
 * @returns {Object} - flat map of dottedName → leaf entry
 */
export function flattenFields(fields, prefix = "", out = {}) {
  for (const [key, val] of Object.entries(fields || {})) {
    const name = prefix ? `${prefix}.${key}` : key;
    if (isLeafField(val)) {
      out[name] = val;
    } else {
      flattenFields(val, name, out);
    }
  }
  return out;
}

/**
 * Extract geometry data from fields response.
 * @param {Object} fields - API response fields object
 * @returns {Object|null} - map of fieldName → { geometry, fieldType }
 */
export function extractGeometry(fields) {
  const geo = {};
  for (const [key, val] of Object.entries(flattenFields(fields))) {
    if (
      val &&
      typeof val === "object" &&
      Array.isArray(val.geometry) &&
      val.geometry.length
    ) {
      geo[key] = {
        geometry: val.geometry,
        fieldType: val.fieldType || "unknown",
        displayName: val.displayName,
      };
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
    for (const [
      fieldName,
      { geometry: geoList, fieldType, displayName },
    ] of Object.entries(fieldGeometry)) {
      for (const geo of geoList) {
        if (!geo.boundingBox) continue;
        if (geo.page && geo.page !== page) continue;
        const { left, top, width, height } = geo.boundingBox;
        boxes.push({
          left,
          top,
          width,
          height,
          fieldName,
          fieldType,
          displayName,
        });
      }
    }

    const merged = mergeOverlappingBoxes(boxes);

    for (const box of merged) {
      const color =
        box.fields.length > 1
          ? TYPE_COLORS.merged
          : TYPE_COLORS[box.fields[0].fieldType] || TYPE_COLORS.unknown;
      const rect = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "rect",
      );
      rect.setAttribute("x", box.left);
      rect.setAttribute("y", box.top);
      rect.setAttribute("width", box.width);
      rect.setAttribute("height", box.height);
      rect.setAttribute("fill", "none");
      rect.setAttribute("stroke", color);
      rect.setAttribute("stroke-width", "0.003");
      // Human-readable label for the tooltip; falls back to the raw name.
      rect.dataset.field = box.fields
        .map((f) => f.displayName || f.fieldName)
        .join("\n");
      // Raw field names (newline-separated) for matching against table rows.
      rect.dataset.fields = box.fields.map((f) => f.fieldName).join("\n");
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

  // Observe the image, not the container: this fires on panel resize *and* on
  // zoom (which changes the image's rendered width but not the container's), so
  // the overlay always re-renders to match the current image size.
  resizeObserver = new ResizeObserver(() => {
    if (container.querySelector("img")) doRender();
  });
  resizeObserver.observe(img);

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
 * Render the extracted-data table as an HTML string.
 * @param {Object} data - API response fields object
 * @param {object} [opts]
 * @param {boolean} [opts.revealed=false] - show values (vs masked dots)
 * @param {boolean} [opts.maskable=true] - render the "Show values" privacy toggle.
 *   When false, values are always shown and no toggle is rendered (demo mode).
 * @returns {string} - table HTML, or "" when there are no fields
 */
export function renderExtractedData(
  data,
  { revealed = false, maskable = true } = {},
) {
  if (typeof data !== "object" || data === null) return "";
  const show = revealed || !maskable;
  const rows = Object.entries(flattenFields(data))
    .map(([key, val]) => {
      const isObj =
        val != null && typeof val === "object" && !Array.isArray(val);
      const conf =
        isObj && typeof val.confidence === "number" ? val.confidence : null;
      const value = isObj && "value" in val ? val.value : val;
      const label = isObj && val.displayName ? val.displayName : key;
      const display =
        value != null && typeof value === "object"
          ? JSON.stringify(value)
          : String(value ?? "-");
      return { key, label, conf, display };
    })
    .sort((a, b) => {
      if (a.conf == null) return b.conf == null ? 0 : 1;
      if (b.conf == null) return -1;
      return a.conf - b.conf;
    })
    .map(({ key, label, conf, display }) => {
      const confCell =
        conf == null
          ? "<td>-</td>"
          : `<td class="${
              conf >= 0.9
                ? "confidence-high"
                : conf >= 0.7
                  ? "confidence-med"
                  : "confidence-low"
            }">${(conf * 100).toFixed(1)}%</td>`;
      const valueContent = show ? esc(display) : "•••••";
      return `<tr data-field="${esc(key)}"><td class="detail-label">${esc(label)}</td><td class="extracted-value" data-value="${esc(display)}">${valueContent}</td>${confCell}</tr>`;
    })
    .join("");
  if (!rows) return "";
  const head = maskable
    ? `<thead><tr><th>Extracted Data</th><th colspan="2" class="extracted-data-toggle-cell"><label class="inline-checkbox"><input type="checkbox" class="extracted-data-toggle"${revealed ? " checked" : ""}> Show values</label></th></tr><tr><th>Field</th><th>Value</th><th>Confidence</th></tr></thead>`
    : `<thead><tr><th>Field</th><th>Value</th><th>Confidence</th></tr></thead>`;
  return `<table class="extracted-data-table"><colgroup><col class="ed-col-field"><col class="ed-col-value"><col class="ed-col-conf"></colgroup>${head}<tbody>${rows}</tbody></table>`;
}

/**
 * Add zoom controls (buttons + Ctrl/Cmd-scroll) to an image preview. Zoom works
 * by widening the image past its fit width; the panel's overflow lets the user
 * pan, and the bbox overlay (which observes the image) re-renders to match.
 * Images only - PDF previews get native browser zoom for free.
 * @param {HTMLElement} container
 * @param {HTMLImageElement} img
 */
function addImageZoom(container, img) {
  const STEP = 1.25;
  const MAX = 5;
  let scale = 1;
  let fitWidth = 0; // image's responsive fit width, captured on first zoom

  const btn = (label, glyph) =>
    h(
      "button",
      {
        type: "button",
        className: "zoom-btn",
        "aria-label": label,
        title: label,
      },
      glyph,
    );
  const out = btn("Zoom out", "−");
  const reset = btn("Reset zoom", "↺");
  const inn = btn("Zoom in", "+");
  const controls = h(
    "div",
    { className: "preview-zoom-controls" },
    out,
    reset,
    inn,
  );
  container.appendChild(controls);

  // The controls live inside the scroll container, so they'd scroll out of view
  // when zoomed. Counter-translate by the scroll offset to pin them top-right.
  const pin = () => {
    controls.style.transform = `translate(${container.scrollLeft}px, ${container.scrollTop}px)`;
  };

  const setZoom = (next) => {
    scale = Math.min(MAX, Math.max(1, next));
    if (scale === 1) {
      img.style.width = "";
      img.style.maxWidth = "";
      fitWidth = 0;
    } else {
      if (!fitWidth) fitWidth = img.clientWidth;
      if (!fitWidth) return; // image not laid out yet
      img.style.maxWidth = "none";
      img.style.width = Math.round(fitWidth * scale) + "px";
    }
    container.classList.toggle("preview-zoomed", scale > 1);
    pin();
  };

  out.addEventListener("click", () => setZoom(scale / STEP));
  reset.addEventListener("click", () => setZoom(1));
  inn.addEventListener("click", () => setZoom(scale * STEP));
  container.addEventListener("scroll", pin);

  container.addEventListener(
    "wheel",
    (e) => {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      setZoom(e.deltaY < 0 ? scale * STEP : scale / STEP);
    },
    { passive: false },
  );

  // Click-and-drag to pan when zoomed.
  let dragging = false;
  let startX = 0;
  let startY = 0;
  let startLeft = 0;
  let startTop = 0;
  container.addEventListener("pointerdown", (e) => {
    if (scale <= 1 || e.button !== 0) return;
    if (e.target.closest(".preview-zoom-controls")) return; // let buttons click
    dragging = true;
    startX = e.clientX;
    startY = e.clientY;
    startLeft = container.scrollLeft;
    startTop = container.scrollTop;
    container.classList.add("preview-dragging");
    container.setPointerCapture(e.pointerId);
    e.preventDefault();
  });
  container.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    container.scrollLeft = startLeft - (e.clientX - startX);
    container.scrollTop = startTop - (e.clientY - startY);
  });
  const endDrag = (e) => {
    if (!dragging) return;
    dragging = false;
    container.classList.remove("preview-dragging");
    try {
      container.releasePointerCapture(e.pointerId);
    } catch {
      /* pointer already released */
    }
  };
  container.addEventListener("pointerup", endDrag);
  container.addEventListener("pointercancel", endDrag);
}

/**
 * Render a document preview (PDF object or watermarked image) into a container.
 * Callers handle fetching the URL and any "previewable type" gating.
 * @param {HTMLElement} container
 * @param {object} opts
 * @param {string} opts.url - presigned preview URL
 * @param {string} opts.contentType
 * @param {string} [opts.watermarkEmail=""] - email tiled over image previews
 */
export function renderPreview(
  container,
  { url, contentType, watermarkEmail = "" },
) {
  if (contentType === "application/pdf") {
    // eslint-disable-next-line no-unsanitized/property -- URL escaped with esc()
    container.innerHTML = `<object data="${esc(url)}" type="application/pdf" class="document-preview-frame"><p>Unable to display PDF preview.</p></object>`;
  } else {
    // eslint-disable-next-line no-unsanitized/property -- URL escaped with esc()
    container.innerHTML = `<img src="${esc(url)}" class="document-preview-img" alt="Document preview" draggable="false" oncontextmenu="return false" onerror="this.parentElement.innerHTML='<p class=empty-state>Preview unavailable</p>'" />`;
    container.classList.add("watermark-block");
    const img = container.querySelector("img");
    if (img) addImageZoom(container, img);
  }
  container.style.setProperty(
    "--watermark-bg",
    `url("data:image/svg+xml,${encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' width='300' height='150'><text x='50%' y='50%' font-family='sans-serif' font-size='18' fill='black' text-anchor='middle' dominant-baseline='middle' transform='rotate(-30 150 75)'>${watermarkEmail}</text></svg>`)}")`,
  );
  container.classList.add("watermarked");
}

/**
 * Wire hover-to-highlight: hovering a field row in the extracted-data table
 * highlights that field's bounding box(es) in the preview. Delegated on the
 * containers, so it survives table re-renders and late/async overlay rendering.
 * Call once after the elements exist (e.g. in the view's mount()).
 * @param {HTMLElement} tableContainer - element that holds the rendered table
 * @param {HTMLElement} previewContainer - element that holds the bbox overlay
 */
export function linkFieldHighlighting(tableContainer, previewContainer) {
  const clearBoxes = () => {
    previewContainer
      .querySelectorAll(".bbox-overlay rect.bbox-highlight")
      .forEach((r) => r.classList.remove("bbox-highlight"));
  };
  const clearRows = () => {
    tableContainer
      .querySelectorAll("tr[data-field].row-highlight")
      .forEach((r) => r.classList.remove("row-highlight"));
  };

  // mouseover bubbles on every child (cells, svg children), so track what's
  // already active and skip redundant work - keeps auto-scroll from re-firing.
  let activeField = null;
  let activeBoxKey = null;

  // Row hover -> highlight the field's box(es) and scroll the first into view.
  tableContainer.addEventListener("mouseover", (e) => {
    const row = e.target.closest("tr[data-field]");
    if (!row || row.dataset.field === activeField) return;
    activeField = row.dataset.field;
    clearBoxes();
    let first = null;
    previewContainer.querySelectorAll(".bbox-overlay rect").forEach((rect) => {
      if ((rect.dataset.fields || "").split("\n").includes(activeField)) {
        rect.classList.add("bbox-highlight");
        if (!first) first = rect;
      }
    });
    if (first)
      first.scrollIntoView({
        block: "nearest",
        inline: "nearest",
        behavior: "smooth",
      });
  });
  tableContainer.addEventListener("mouseleave", () => {
    clearBoxes();
    activeField = null;
  });

  // Box hover -> highlight the matching field row(s) and scroll the first into
  // view. Closes the loop so preview and table read as one linked surface.
  previewContainer.addEventListener("mouseover", (e) => {
    const rect = e.target.closest(".bbox-overlay rect");
    if (!rect) return;
    const key = rect.dataset.fields || "";
    if (key === activeBoxKey) return;
    activeBoxKey = key;
    clearRows();
    const fields = key.split("\n");
    let first = null;
    tableContainer.querySelectorAll("tr[data-field]").forEach((row) => {
      if (fields.includes(row.dataset.field)) {
        row.classList.add("row-highlight");
        if (!first) first = row;
      }
    });
    if (first)
      first.scrollIntoView({
        block: "nearest",
        inline: "nearest",
        behavior: "smooth",
      });
  });
  previewContainer.addEventListener("mouseleave", () => {
    clearRows();
    activeBoxKey = null;
  });
}

/**
 * Mark field rows that have bounding-box geometry, so the table signals which
 * fields are locatable in the preview *before* the user hovers. Pairs with the
 * `.has-geometry` styling (accent + pointer cursor) and linkFieldHighlighting().
 * Idempotent: re-applies cleanly on table/geometry changes.
 * @param {HTMLElement} tableContainer - element that holds the rendered table
 * @param {Object|null} fieldGeometry - output of extractGeometry()
 */
export function markFieldsWithGeometry(tableContainer, fieldGeometry) {
  const geo = fieldGeometry || {};
  tableContainer.querySelectorAll("tr[data-field]").forEach((row) => {
    const field = geo[row.dataset.field];
    row.classList.toggle("has-geometry", Boolean(field));
    if (field) {
      // Tint the row accent to match the field's box color, so the row↔box
      // mapping reads at a glance. (Merged boxes render gray; the row keeps its
      // own type color rather than the merge color.)
      row.style.setProperty(
        "--field-color",
        TYPE_COLORS[field.fieldType] || TYPE_COLORS.unknown,
      );
    } else {
      row.style.removeProperty("--field-color");
    }
  });
}
