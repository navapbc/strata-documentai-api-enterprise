/**
 * Shared document viewer components.
 * Renders preview with bbox overlay and extracted fields table.
 */

import { mergeOverlappingBoxes } from "../utils/bbox.js";
import { esc } from "../utils/helpers.js";
import { h, svgIcon } from "../utils/dom.js";
import {
  ICON_ZOOM_OUT,
  ICON_ZOOM_IN,
  ICON_ROTATE_LEFT,
  ICON_ROTATE_RIGHT,
} from "../utils/icons.js";

const BBOX_ROTATE = {
  90: ({ left, top, width, height }) => ({
    left: 1 - top - height,
    top: left,
    width: height,
    height: width,
  }),
  180: ({ left, top, width, height }) => ({
    left: 1 - left - width,
    top: 1 - top - height,
    width,
    height,
  }),
  270: ({ left, top, width, height }) => ({
    left: top,
    top: 1 - left - width,
    width: height,
    height: width,
  }),
};

export const PREVIEWABLE_TYPES = ["application/pdf", "image/jpeg", "image/png"];

/** Width of container minus its horizontal padding — the space content should fill. */
function fitWidth(container) {
  const cs = getComputedStyle(container);
  return (
    container.clientWidth -
    parseFloat(cs.paddingLeft) -
    parseFloat(cs.paddingRight)
  );
}

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
 * @returns {{observer: ResizeObserver|null, rerender: () => void}} - observer
 *   to disconnect on cleanup; rerender redraws the overlay (e.g. after rotate)
 */
export function renderBboxOverlay(container, fieldGeometry) {
  clearBboxOverlay(container);
  const none = { observer: null, rerender: () => {} };
  if (!fieldGeometry) return none;

  const pageEls = container.querySelectorAll(".pdf-page");
  const isPdf = pageEls.length > 0;
  const img = !isPdf && container.querySelector("img");
  if (!isPdf && !img) return none;

  const renderPdfOverlays = () => {
    const rot = container.querySelector(".pdf-scroll")?._rotation || 0;
    container.querySelectorAll(".pdf-page").forEach((pageEl) => {
      const canvas = pageEl.querySelector("canvas");
      if (!canvas) return;
      const pageNum = Number(pageEl.dataset.page);
      const boxes = [];
      for (const [
        fieldName,
        { geometry: geoList, fieldType, displayName },
      ] of Object.entries(fieldGeometry)) {
        for (const entry of geoList) {
          if (
            !entry.boundingBox ||
            (entry.page != null && entry.page !== pageNum)
          )
            continue;
          boxes.push({
            ...(BBOX_ROTATE[rot] ?? ((b) => b))(entry.boundingBox),
            fieldName,
            fieldType,
            displayName,
          });
        }
      }
      if (!boxes.length) return;
      const wrap = _buildOverlayWrap(
        mergeOverlappingBoxes(boxes),
        canvas.offsetWidth,
        canvas.offsetHeight,
        0,
      );
      wrap.style.top = canvas.offsetTop + "px";
      wrap.style.left = canvas.offsetLeft + "px";
      pageEl.appendChild(wrap);
    });
  };

  const renderImageOverlay = () => {
    const rotation = container._previewRotation || 0;
    const wrap = _buildOverlayWrap(
      mergeOverlappingBoxes(
        Object.entries(fieldGeometry).flatMap(
          ([fieldName, { geometry: geoList, fieldType, displayName }]) =>
            geoList
              .filter((g) => g.boundingBox)
              .map(({ boundingBox: { left, top, width, height } }) => ({
                left,
                top,
                width,
                height,
                fieldName,
                fieldType,
                displayName,
              })),
        ),
      ),
      img.offsetWidth,
      img.offsetHeight,
      rotation,
    );
    wrap.style.top = img.offsetTop + "px";
    wrap.style.left = img.offsetLeft + "px";
    container.appendChild(wrap);
  };

  const doRender = () => {
    clearBboxOverlay(container);
    if (isPdf) renderPdfOverlays();
    else renderImageOverlay();
  };

  doRender();

  const observed = isPdf ? container.querySelector(".pdf-page canvas") : img;
  if (observed) {
    const resizeObserver = new ResizeObserver(doRender);
    resizeObserver.observe(observed);
    return { observer: resizeObserver, rerender: doRender };
  }
  return { observer: null, rerender: doRender };
}

function _buildOverlayWrap(merged, width, height, rotation) {
  const wrap = document.createElement("div");
  wrap.className = "bbox-overlay-wrap";
  wrap.style.width = width + "px";
  wrap.style.height = height + "px";
  if (rotation) {
    wrap.style.transform = `rotate(${rotation}deg)`;
    wrap.style.transformOrigin = "center center";
  }

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.classList.add("bbox-overlay");
  svg.setAttribute("viewBox", "0 0 1 1");
  svg.setAttribute("preserveAspectRatio", "none");

  const tooltip = document.createElement("div");
  tooltip.className = "bbox-tooltip";
  tooltip.style.display = "none";

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
    rect.dataset.field = box.fields
      .map((f) => f.displayName || f.fieldName)
      .join("\n");
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
  return wrap;
}

/**
 * Remove any existing bbox overlay from a container.
 * @param {HTMLElement} container
 */
export function clearBboxOverlay(container) {
  container.querySelectorAll(".bbox-overlay-wrap").forEach((el) => el.remove());
}

/**
 * Render the extracted-data table as an HTML string.
 * @param {Object} data - API response fields object
 * @param {object} [opts]
 * @param {boolean} [opts.revealed=false] - show values (vs masked dots)
 * @param {boolean} [opts.maskable=true] - render the "Show values" presentation mode toggle.
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
/**
 * Shared zoom controls: buttons, Ctrl/Cmd-scroll, drag-to-pan.
 * @param {HTMLElement} container - scrollable panel
 * @param {object} opts
 * @param {() => number} opts.getMaxScale
 * @param {(scale: number) => void} opts.onZoom - called with new scale after clamping
 * @param {boolean} [opts.withRotate=false] - include rotate buttons
 * @param {(deg: number) => void} [opts.onRotate]
 * @returns {{ setZoom: (n: number) => void, scale: () => number }}
 */
function _createZoomControls(
  container,
  { getMaxScale, onZoom, withRotate = false, onRotate } = {},
) {
  const STEP = 1.25;
  let scale = 1;

  const makeButton = (label, icon) => {
    const el = h("button", {
      type: "button",
      className: "zoom-btn",
      "aria-label": label,
      title: label,
    });
    el.appendChild(svgIcon(icon));
    return el;
  };

  const zoomOut = makeButton("Zoom out", ICON_ZOOM_OUT);
  const zoomIn = makeButton("Zoom in", ICON_ZOOM_IN);
  zoomOut.disabled = true;

  const children = [];
  if (withRotate) {
    children.push(
      makeButton("Rotate left", ICON_ROTATE_LEFT),
      makeButton("Rotate right", ICON_ROTATE_RIGHT),
    );
    children.push(h("div", { className: "preview-controls-sep" }));
    children[0].addEventListener("click", () => onRotate?.(-90));
    children[1].addEventListener("click", () => onRotate?.(90));
  }
  children.push(zoomOut, zoomIn);

  const controls = h(
    "div",
    { className: "preview-zoom-controls" },
    ...children,
  );
  container.appendChild(controls);

  const pinControls = () => {
    controls.style.transform = `translate(${container.scrollLeft}px, ${container.scrollTop}px)`;
  };

  const setZoom = async (next) => {
    const max = getMaxScale();
    const scrollFraction = (pos, size, view) =>
      size > view ? pos / (size - view) : 0;
    const scrollFracX = scrollFraction(
      container.scrollLeft,
      container.scrollWidth,
      container.clientWidth,
    );
    const scrollFracY = scrollFraction(
      container.scrollTop,
      container.scrollHeight,
      container.clientHeight,
    );
    scale = Math.min(max, Math.max(1, next));
    zoomOut.disabled = scale <= 1;
    zoomIn.disabled = scale >= max;
    controls.style.transform = "";
    await onZoom(scale);
    container.scrollLeft =
      scrollFracX * (container.scrollWidth - container.clientWidth);
    container.scrollTop =
      scrollFracY * (container.scrollHeight - container.clientHeight);
    pinControls();
  };

  zoomOut.addEventListener("click", () => setZoom(scale / STEP));
  zoomIn.addEventListener("click", () => setZoom(scale * STEP));
  container.addEventListener("scroll", pinControls);
  container.addEventListener(
    "wheel",
    (e) => {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      setZoom(e.deltaY < 0 ? scale * STEP : scale / STEP);
    },
    { passive: false },
  );

  let dragging = false,
    startX = 0,
    startY = 0,
    startLeft = 0,
    startTop = 0;
  container.addEventListener("pointerdown", (e) => {
    if (scale <= 1 || e.button !== 0) return;
    if (e.target.closest(".preview-zoom-controls")) return;
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
      /* released */
    }
  };
  container.addEventListener("pointerup", endDrag);
  container.addEventListener("pointercancel", endDrag);

  return { setZoom, scale: () => scale };
}

function addImageZoom(container, img, { onRotate } = {}) {
  let rotation = 0;
  let currentScale = 1;

  const applyLayout = (scale) => {
    currentScale = scale;
    const isSideways = rotation === 90 || rotation === 270;
    img.style.margin = "";
    if (scale === 1 && !isSideways) {
      img.style.width =
        img.style.height =
        img.style.maxWidth =
        img.style.maxHeight =
        img.style.flexShrink =
          "";
    } else if (img.naturalWidth) {
      const natVis = isSideways ? img.naturalHeight : img.naturalWidth;
      const vis = Math.min(fitWidth(container), natVis) * scale;
      const aspect = img.naturalWidth / img.naturalHeight;
      const imgWidth = Math.round(isSideways ? vis * aspect : vis);
      const imgHeight = Math.round(isSideways ? vis : vis / aspect);
      img.style.maxWidth = img.style.maxHeight = "none";
      img.style.flexShrink = "0";
      img.style.width = imgWidth + "px";
      img.style.height = imgHeight + "px";
      if (isSideways)
        img.style.margin = `${(imgWidth - imgHeight) / 2}px ${(imgHeight - imgWidth) / 2}px`;
    }
    img.style.transform = rotation ? `rotate(${rotation}deg)` : "";
    container._previewRotation = rotation;
    container.classList.toggle("preview-zoomed", scale > 1);
    requestAnimationFrame(() => onRotate?.());
  };

  const getMaxScale = () => {
    const isSideways = rotation === 90 || rotation === 270;
    const natVis = isSideways ? img.naturalHeight : img.naturalWidth;
    const fit = Math.min(fitWidth(container), natVis);
    return fit > 0 ? natVis / fit : 1;
  };

  const { setZoom } = _createZoomControls(container, {
    getMaxScale,
    onZoom: applyLayout,
    withRotate: true,
    onRotate: (delta) => {
      rotation = (((rotation + delta) % 360) + 360) % 360;
      setZoom(1);
      container.scrollLeft = container.scrollTop = 0;
    },
  });

  if (img.complete && img.naturalWidth) applyLayout(currentScale);
  else
    img.addEventListener("load", () => applyLayout(currentScale), {
      once: true,
    });
}

export async function renderPdfPreview(
  container,
  url,
  { pdfjsLib, onRender } = {},
) {
  if (!pdfjsLib) {
    container.innerHTML = `<object data="${esc(url)}" type="application/pdf" class="document-preview-frame"><p class="empty-state">Preview unavailable</p></object>`;
    return;
  }
  if (!pdfjsLib.GlobalWorkerOptions.workerSrc) {
    pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
      "/dist/pdf.worker.min.mjs",
      location.origin,
    ).href;
  }

  // previewToken guards against a new document being selected while this one
  // is still fetching - renderPreview bumps container._previewToken on every
  // call so a stale load can detect it was superseded and bail out.
  const previewToken = (container._previewToken =
    (container._previewToken ?? 0) + 1);

  container.innerHTML = '<p class="empty-state">Loading PDF…</p>';

  let pdf;
  try {
    pdf = await pdfjsLib.getDocument(url).promise;
  } catch (e) {
    if (previewToken === container._previewToken)
      container.innerHTML = `<p class="empty-state">Preview unavailable: ${esc(String(e?.message || e))}</p>`;
    return;
  }

  if (previewToken !== container._previewToken) {
    pdf.destroy();
    return;
  }

  container._pdfDoc?.destroy();
  container._pdfDoc = pdf;
  container.innerHTML = "";

  const dpr = window.devicePixelRatio || 1;

  const scrollWrap = document.createElement("div");
  scrollWrap.className = "pdf-scroll-wrap";
  const scroll = document.createElement("div");
  scroll.className = "pdf-scroll";
  scrollWrap.appendChild(scroll);
  container.appendChild(scrollWrap);

  let rotation = 0;
  // naturalW/H are captured after each render so applyScale always multiplies
  // from the true unscaled dimensions, not from a previously-scaled scrollWidth.
  let naturalW = 0;
  let naturalH = 0;
  let token = 0;

  const renderAllPages = async () => {
    // renderToken guards against concurrent renders within this document
    // (e.g. rotate fired twice quickly) - a new call increments token so the
    // previous loop detects it's stale and stops writing to the DOM.
    const renderToken = ++token;
    const stale = () =>
      renderToken !== token || previewToken !== container._previewToken;
    scroll._rotation = rotation;
    scroll.replaceChildren();
    for (let i = 1; i <= pdf.numPages; i++) {
      if (stale()) return;

      try {
        const page = await pdf.getPage(i);
        if (stale()) return;
        const baseViewport = page.getViewport({ scale: 1, rotation });
        const cssScale = (fitWidth(container) || 800) / baseViewport.width;
        const viewport = page.getViewport({ scale: cssScale * dpr, rotation });

        const canvas = document.createElement("canvas");
        canvas.className = "document-preview-canvas";
        // Canvas buffer is dpr times the CSS size for sharp rendering on retina displays.
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        canvas.style.width = viewport.width / dpr + "px";
        canvas.style.height = viewport.height / dpr + "px";

        // Explicit pixel width prevents .pdf-page { width: 100% } from
        // interfering with transform: scale() zoom - only the transform scales it.
        scroll.style.width = viewport.width / dpr + "px";

        const pageEl = document.createElement("div");
        pageEl.className = "pdf-page";
        pageEl.dataset.page = i;
        pageEl.appendChild(canvas);
        scroll.appendChild(pageEl);

        await page.render({ canvasContext: canvas.getContext("2d"), viewport })
          .promise;
        if (stale()) return;
      } catch (e) {
        // pdf.js rejects in-flight getPage/render promises when the document is
        // destroyed by a superseding load. Swallow the error if we're stale;
        // otherwise re-throw so real errors surface.
        if (stale()) return;
        throw e;
      }
    }
    naturalW = scroll.scrollWidth;
    naturalH = scroll.scrollHeight;
    onRender?.();
  };

  const applyScale = (scale) => {
    scroll.style.transform = scale === 1 ? "" : `scale(${scale})`;
    scroll.style.transformOrigin = "top left";
    scrollWrap.style.width = naturalW * scale + "px";
    scrollWrap.style.height = naturalH * scale + "px";
    container.classList.toggle("preview-zoomed", scale > 1);
  };

  const { scale: getScale } = _createZoomControls(container, {
    getMaxScale: () => 2,
    onZoom: applyScale,
    withRotate: true,
    onRotate: async (delta) => {
      rotation = (((rotation + delta) % 360) + 360) % 360;
      await renderAllPages();
      applyScale(getScale());
      container.scrollLeft = container.scrollTop = 0;
    },
  });

  await renderAllPages();
  applyScale(1);

  // Re-render pages when the panel is resized so they refit to the new width.
  // lastRenderedWidth skips the initial observer fire and pure-height changes.
  // Debounced to avoid hammering pdf.js while the splitter is being dragged.
  let lastRenderedWidth = fitWidth(container);
  let resizeTimer;
  const resizeObserver = new ResizeObserver(() => {
    if (previewToken !== container._previewToken) {
      resizeObserver.disconnect();
      return;
    }
    if (Math.abs(fitWidth(container) - lastRenderedWidth) <= 1) return;
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(async () => {
      if (previewToken !== container._previewToken) return;
      lastRenderedWidth = fitWidth(container);
      await renderAllPages();
      applyScale(getScale());
    }, 150);
  });
  resizeObserver.observe(container);
}

/**
 * Render a document preview (pdf.js canvas or watermarked image) into a container.
 * @param {HTMLElement} container
 * @param {object} opts
 * @param {string} opts.url - presigned preview URL
 * @param {string} opts.contentType
 * @param {string} [opts.watermarkEmail=""] - email tiled over image previews
 * @param {Function} [opts.onRotate]
 * @param {Function} [opts.onRender] - called after all pages are drawn (PDF) or image loads
 * @param {object} [opts.pdfjsLib]
 */
export function renderPreview(
  container,
  { url, contentType, watermarkEmail = "", onRotate, onRender, pdfjsLib } = {},
) {
  container._previewRotation = 0;
  container._previewToken = (container._previewToken ?? 0) + 1;
  // Apply watermark setup for all content types so PDFs get it too.
  container.classList.add("watermark-block");
  container.style.setProperty(
    "--watermark-bg",
    `url("data:image/svg+xml,${encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' width='300' height='150'><text x='50%' y='50%' font-family='sans-serif' font-size='18' fill='black' text-anchor='middle' dominant-baseline='middle' transform='rotate(-30 150 75)'>${watermarkEmail}</text></svg>`)}")`,
  );
  container.classList.add("watermarked");

  if (contentType === "application/pdf") {
    renderPdfPreview(container, url, { pdfjsLib, onRender });
    return;
  }
  // Built with DOM APIs + listeners, not inline on* attributes: the deployed
  // CSP (script-src 'self') blocks inline event handlers.
  const img = document.createElement("img");
  img.className = "document-preview-img";
  img.alt = "Document preview";
  img.draggable = false;
  img.addEventListener("contextmenu", (e) => e.preventDefault());
  img.addEventListener("error", () => {
    container.innerHTML = '<p class="empty-state">Preview unavailable</p>';
  });
  img.src = url;
  container.replaceChildren(img);
  addImageZoom(container, img, { onRotate });
  const markOrientation = () => {
    container.classList.toggle(
      "preview-landscape",
      img.naturalWidth > img.naturalHeight,
    );
  };
  if (img.complete && img.naturalWidth) markOrientation();
  else img.addEventListener("load", markOrientation, { once: true });
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
