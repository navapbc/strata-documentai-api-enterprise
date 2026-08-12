/**
 * Document viewer pane - two-panel preview + detail.
 *
 * Usage:
 *   const pane = mount(root);
 *   pane.show(docs);        // render a list of docs grouped by date, auto-select first
 *   pane.select(jobId);     // load detail + preview for a specific job
 *   pane.clear();
 *   pane.unmount();
 */
import * as DocumentsService from "../services/documents.js";
import * as Helpers from "../utils/helpers.js";
import * as Session from "../utils/session.js";
import { h } from "../utils/dom.js";
import { tpl } from "../utils/tpl.js";
import {
  extractGeometry,
  renderBboxOverlay,
  clearBboxOverlay,
  renderExtractedData,
  renderPreview,
  linkFieldHighlighting,
  markFieldsWithGeometry,
  PREVIEWABLE_TYPES,
} from "../../../shared/components/document-viewer.js";
import html from "./document-viewer-pane.html";

const tmpl = tpl(html);

export function mount(root) {
  root.replaceChildren(tmpl());

  const previewPanel = root.querySelector("#doc-pane-preview");
  const detailContent = root.querySelector("#doc-pane-detail-content");
  const backBtn = root.querySelector("#doc-viewer-back");

  let activeJobId = null;
  let fieldGeometry = null;
  let resizeObserver = null;

  linkFieldHighlighting(detailContent, previewPanel);

  // Mobile/tablet: the list and detail share one narrow column, so selecting
  // a document switches to a full-width detail view instead of showing both
  // at once. Desktop's wide layout ignores this class entirely.
  function showMobileDetail() {
    root.closest(".filter-layout--doc-viewer")?.classList.add("mobile-detail-active");
  }

  backBtn.addEventListener("click", () => {
    root.closest(".filter-layout--doc-viewer")?.classList.remove("mobile-detail-active");
  });

  function hide() {
    activeJobId = null;
    root.style.display = "none";
  }

  function clear() {
    activeJobId = null;
    fieldGeometry = null;
    if (resizeObserver) {
      resizeObserver.disconnect();
      resizeObserver = null;
    }
    clearBboxOverlay(previewPanel);
    detailContent.innerHTML = "";
    root.style.display = "";
    previewPanel.innerHTML = '<p class="empty-state">Select a document to preview</p>';
    previewPanel.classList.remove("watermarked", "watermark-block");
  }

  function unmount() {
    if (resizeObserver) {
      resizeObserver.disconnect();
      resizeObserver = null;
    }
    root.replaceChildren();
  }

  function groupByDate(docs) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const groups = new Map();
    for (const doc of docs) {
      const d = new Date(doc.createdAt);
      d.setHours(0, 0, 0, 0);
      let label;
      if (d.getTime() === today.getTime()) label = "Today";
      else if (d.getTime() === yesterday.getTime()) label = "Yesterday";
      else
        label = d.toLocaleDateString(undefined, {
          month: "short",
          day: "numeric",
          year: d.getFullYear() !== today.getFullYear() ? "numeric" : undefined,
        });
      if (!groups.has(label)) groups.set(label, []);
      groups.get(label).push(doc);
    }
    return groups;
  }

  function buildListItem(listEl, doc) {
    const cls =
      doc.processStatus === "success"
        ? "badge-success"
        : doc.processStatus === "failed"
          ? "badge-danger"
          : "badge-neutral";
    const badge = doc.processStatus
      ? h("span", { className: `badge ${cls}` }, doc.processStatus)
      : null;
    const li = h(
      "li",
      {
        className: `doc-list-item${doc.jobId === activeJobId ? " active" : ""}`,
        "data-job-id": doc.jobId,
      },
      h("div", { className: "doc-list-name" }, doc.fileName || doc.jobId?.slice(0, 8) || "-"),
      ...(badge ? [badge] : []),
    );
    li.addEventListener("click", () => {
      activeJobId = doc.jobId;
      listEl.querySelectorAll(".doc-list-item").forEach((el) => el.classList.remove("active"));
      li.classList.add("active");
      loadDetail(doc.jobId);
      showMobileDetail();
    });
    return li;
  }

  function show(listEl, docs, { autoSelect = true } = {}) {
    listEl.innerHTML = "";
    const groups = groupByDate(docs);
    for (const [label, group] of groups) {
      listEl.appendChild(h("li", { className: "doc-list-heading metrics-timeframe-label" }, label));
      for (const doc of group) {
        listEl.appendChild(buildListItem(listEl, doc));
      }
    }
    if (autoSelect && docs.length) {
      activeJobId = docs[0].jobId;
      listEl.querySelector(`[data-job-id="${docs[0].jobId}"]`)?.classList.add("active");
      loadDetail(docs[0].jobId);
    }
  }

  function append(listEl, docs) {
    const groups = groupByDate(docs);
    for (const [label, group] of groups) {
      // Only add a heading if it doesn't already exist in the list
      const existing = [...listEl.querySelectorAll(".doc-list-heading")].find(
        (el) => el.textContent === label,
      );
      if (!existing) {
        listEl.appendChild(
          h("li", { className: "doc-list-heading metrics-timeframe-label" }, label),
        );
      }
      for (const doc of group) {
        listEl.appendChild(buildListItem(listEl, doc));
      }
    }
  }

  async function select(listEl, jobId) {
    activeJobId = jobId;
    listEl.querySelectorAll(".doc-list-item").forEach((el) => el.classList.remove("active"));
    listEl.querySelector(`[data-job-id="${jobId}"]`)?.classList.add("active");
    await loadDetail(jobId);
  }

  async function loadDetail(jobId) {
    detailContent.textContent = "Loading...";
    fieldGeometry = null;
    if (resizeObserver) {
      resizeObserver.disconnect();
      resizeObserver = null;
    }
    clearBboxOverlay(previewPanel);
    try {
      const detail = await DocumentsService.get(jobId, {
        includeExtractedData: true,
        includeBoundingBox: true,
      });
      if (detail.fields) fieldGeometry = extractGeometry(detail.fields);
      renderDetail(detail);
      await loadPreview(jobId, detail.contentType, detail.processStatus);
      if (fieldGeometry) {
        resizeObserver = renderBboxOverlay(previewPanel, fieldGeometry);
        markFieldsWithGeometry(detailContent, fieldGeometry);
      } else {
        if (!detailContent.querySelector(".bbox-unavailable-note")) {
          const p = document.createElement("p");
          p.className = "bbox-unavailable-note empty-state";
          p.textContent = "Bounding box data is not available for this document.";
          detailContent.appendChild(p);
        }
      }
    } catch (e) {
      detailContent.textContent = e.message;
    }
  }

  async function loadPreview(jobId, contentType, processStatus) {
    if (processStatus === "password_protected") {
      previewPanel.innerHTML =
        '<p class="empty-state">Preview unavailable - document is password protected</p>';
      return;
    }
    if (!PREVIEWABLE_TYPES.includes(contentType)) {
      previewPanel.innerHTML =
        '<p class="empty-state">Preview not available for this file type</p>';
      return;
    }
    previewPanel.innerHTML = '<p class="empty-state">Loading preview…</p>';
    try {
      const resp = await DocumentsService.getPreviewUrl(jobId);
      renderPreview(previewPanel, {
        url: resp.url,
        contentType,
        watermarkEmail: Session.getEmail() || "",
      });
    } catch {
      previewPanel.innerHTML = '<p class="empty-state">Preview unavailable</p>';
      previewPanel.classList.remove("watermarked", "watermark-block");
    }
  }

  function renderDetail(doc) {
    const sections = [
      renderSection("Overview", [
        ["Job ID", doc.jobId],
        ["File Name", doc.fileName],
        ["Status", doc.processStatus],
        ["Category", doc.documentCategory],
        ["Tenant", doc.tenantId],
        ["API Key", doc.apiKeyName],
        ["External ID", doc.externalDocumentId],
        ["Batch ID", doc.batchId],
      ]),
      renderSection("Classification", [
        ["Matched Blueprint", doc.matchedBlueprint],
        [
          "Blueprint Confidence",
          doc.matchedBlueprintConfidence != null
            ? `${(doc.matchedBlueprintConfidence * 100).toFixed(1)}%`
            : "-",
        ],
        ["Document Class", doc.matchedDocumentClass],
      ]),
      renderSection("Processing", [
        ["Created", doc.createdAt],
        ["Processed", doc.processedDate],
        [
          "Total Time",
          doc.totalProcessingTimeSeconds != null ? `${doc.totalProcessingTimeSeconds}s` : "-",
        ],
        [
          "BDA Time",
          doc.bdaProcessingTimeSeconds != null ? `${doc.bdaProcessingTimeSeconds}s` : "-",
        ],
        ["BDA Region", doc.bdaRegionUsed],
        ["Retries", doc.retryCount],
        ["Error", doc.errorMessage],
      ]),
      renderSection("File", [
        ["Content Type", doc.contentType],
        ["Size", doc.fileSizeBytes != null ? `${(doc.fileSizeBytes / 1024).toFixed(1)} KB` : "-"],
        ["Pages", doc.pagesDetected],
      ]),
    ];
    if (doc.fields) {
      sections.push(renderExtractedData(doc.fields, { revealed: true, maskable: false }));
    }
    // eslint-disable-next-line no-unsanitized/property -- server data rendered with esc()
    detailContent.innerHTML = sections.join("");
  }

  function renderSection(title, fields) {
    const rows = fields
      .filter(([, val]) => val != null && val !== "" && val !== "-")
      .map(
        ([label, val]) =>
          `<tr><td class="detail-label">${Helpers.esc(label)}</td><td>${Helpers.esc(String(val))}</td></tr>`,
      )
      .join("");
    if (!rows) return "";
    return `<table class="detail-table"><thead><tr><th colspan="2">${Helpers.esc(title)}</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  function hasSelection() {
    return activeJobId !== null;
  }

  return { show, append, select, clear, hide, hasSelection, unmount };
}
