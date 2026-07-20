import * as DocumentsService from "../../services/documents.js";
import * as Helpers from "../../utils/helpers.js";
import * as Session from "../../utils/session.js";
import * as TenantContext from "../../utils/tenant-context.js";
import { h } from "../../utils/dom.js";
import { tpl } from "../../utils/tpl.js";
import {
  extractGeometry,
  renderBboxOverlay,
  clearBboxOverlay,
  renderExtractedData,
  renderPreview,
  linkFieldHighlighting,
  markFieldsWithGeometry,
  PREVIEWABLE_TYPES,
} from "../../../../shared/components/document-viewer.js";
import html from "./documents.html";

const tmpl = tpl(html);

const STORAGE_KEY_ACTIVE = "docai_documents_active_job";

let _root, _listEl, _noDocuments;
let _statusFilter, _detailPanel, _previewPanel, _detailContent, _collapseBtn;
let _activeJobId = null;
let _detailCollapsed = true;
let _fieldGeometry = null;
let _resizeObserver = null;
let _unsubTenant = null;
let _recentDocuments = [];

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  Helpers.setViewActions();

  _activeJobId = null;
  _detailCollapsed = true;
  _fieldGeometry = null;
  _resizeObserver = null;
  _recentDocuments = [];

  _statusFilter = root.querySelector("#document-status-filter");
  _listEl = root.querySelector("#documents-list");
  _noDocuments = root.querySelector("#no-documents");
  _detailPanel = root.querySelector("#document-detail-panel");
  _previewPanel = root.querySelector("#document-preview-panel");
  _detailContent = root.querySelector("#detail-content");
  _collapseBtn = root.querySelector("#detail-collapse-btn");

  _collapseBtn.addEventListener("click", toggleDetailPanel);
  _collapseBtn.classList.add("disabled");

  linkFieldHighlighting(_detailContent, _previewPanel);

  _statusFilter.addEventListener("change", () => load());

  _unsubTenant = TenantContext.onChange(() => {
    _activeJobId = null;
    sessionStorage.removeItem(STORAGE_KEY_ACTIVE);
    clearDetail();
    // Collapse the detail panel
    _detailCollapsed = true;
    _detailPanel.classList.add("collapsed");
    _root.querySelector(".documents-three-panel").classList.add("detail-collapsed");
    _collapseBtn.textContent = "\u276E";
    _collapseBtn.title = "Expand details";
    // Clear bbox overlay
    clearBboxOverlay(_previewPanel);
    if (_resizeObserver) {
      _resizeObserver.disconnect();
      _resizeObserver = null;
    }
    _fieldGeometry = null;
    load();
  });

  load();
}

export function unmount(root) {
  if (_resizeObserver) {
    _resizeObserver.disconnect();
    _resizeObserver = null;
  }
  if (_unsubTenant) {
    _unsubTenant();
    _unsubTenant = null;
  }
  root.replaceChildren();
}

function clearDetail() {
  _detailContent.innerHTML = "";
  _previewPanel.innerHTML = '<p class="empty-state">Select a document to preview</p>';
  _previewPanel.classList.remove("watermarked", "watermark-block");
  _collapseBtn.classList.add("disabled");
}

function expandDetailPanel() {
  if (!_detailCollapsed) return;
  _detailCollapsed = false;
  _detailPanel.classList.remove("collapsed");
  _root.querySelector(".documents-three-panel").classList.remove("detail-collapsed");
  _collapseBtn.textContent = "\u276F";
  _collapseBtn.title = "Collapse details";
  _collapseBtn.classList.remove("disabled");
}

function toggleDetailPanel() {
  const hasContent = _detailContent.innerHTML.trim().length > 0;
  if (_detailCollapsed && !hasContent) return;
  _detailCollapsed = !_detailCollapsed;
  _detailPanel.classList.toggle("collapsed", _detailCollapsed);
  _root
    .querySelector(".documents-three-panel")
    .classList.toggle("detail-collapsed", _detailCollapsed);
  _collapseBtn.textContent = _detailCollapsed ? "\u276E" : "\u276F";
  _collapseBtn.title = _detailCollapsed ? "Expand details" : "Collapse details";
}

export async function load() {
  const tenantId = TenantContext.getTenantId();
  if (!tenantId) {
    _recentDocuments = [];
    renderList();
    _noDocuments.textContent = "Select a tenant to view recent documents";
    _noDocuments.classList.remove("hidden");
    return;
  }

  const status = _statusFilter?.value || undefined;

  try {
    const resp = await DocumentsService.list({ tenantId, status, limit: 25 });
    _recentDocuments = resp.documents || resp || [];
  } catch {
    _recentDocuments = [];
  }

  renderList();

  const savedActive = sessionStorage.getItem(STORAGE_KEY_ACTIVE);
  if (savedActive) {
    _activeJobId = savedActive;
    const el = _listEl.querySelector(`[data-job-id="${savedActive}"]`);
    if (el) el.classList.add("active");
    loadDetail(savedActive);
  }
}

function renderList() {
  _listEl.innerHTML = "";

  if (!_recentDocuments.length) {
    const msg = TenantContext.getTenantId()
      ? "No documents found"
      : "Select a tenant to view recent documents";
    _noDocuments.textContent = msg;
    _noDocuments.classList.remove("hidden");
    return;
  }

  _noDocuments.classList.add("hidden");
  for (const doc of _recentDocuments) {
    _listEl.appendChild(buildListItem(doc));
  }
}

function buildListItem(doc) {
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
      className: `doc-list-item${doc.jobId === _activeJobId ? " active" : ""}`,
      "data-job-id": doc.jobId,
    },
    h("div", { className: "doc-list-name" }, doc.fileName || doc.jobId?.slice(0, 8) || "-"),
    h(
      "div",
      { className: "doc-list-meta" },
      ...(badge ? [badge] : []),
      h("span", { className: "doc-list-date" }, Helpers.formatDate(doc.createdAt)),
    ),
  );
  li.addEventListener("click", () => {
    _activeJobId = doc.jobId;
    sessionStorage.setItem(STORAGE_KEY_ACTIVE, doc.jobId);
    _listEl.querySelectorAll(".doc-list-item").forEach((el) => el.classList.remove("active"));
    li.classList.add("active");
    loadDetail(doc.jobId);
  });
  return li;
}

async function loadDetail(jobId) {
  _detailContent.textContent = "Loading...";
  _fieldGeometry = null;
  if (_resizeObserver) {
    _resizeObserver.disconnect();
    _resizeObserver = null;
  }
  clearBboxOverlay(_previewPanel);
  try {
    const detail = await DocumentsService.get(jobId, {
      includeExtractedData: true,
      includeBoundingBox: true,
    });
    if (detail.fields) {
      _fieldGeometry = extractGeometry(detail.fields);
    }
    renderDetail(detail);
    expandDetailPanel();
    await loadPreview(jobId, detail.contentType);
    if (_fieldGeometry) {
      _resizeObserver = renderBboxOverlay(_previewPanel, _fieldGeometry);
      markFieldsWithGeometry(_detailContent, _fieldGeometry);
    } else if (detail.fields) {
      // Textract AnalyzeID doesn't return geometry; show a note so the
      // absence of bounding boxes isn't mistaken for a bug.
      const note = document.createElement("p");
      note.className = "empty-state bbox-unavailable-note";
      note.textContent = "Bounding boxes not available for this document";
      _previewPanel.appendChild(note);
    }
  } catch (e) {
    _detailContent.textContent = e.message;
    expandDetailPanel();
  }
}

async function loadPreview(jobId, contentType) {
  if (!PREVIEWABLE_TYPES.includes(contentType)) {
    _previewPanel.innerHTML = '<p class="empty-state">Preview not available for this file type</p>';
    return;
  }

  _previewPanel.innerHTML = '<p class="empty-state">Loading preview…</p>';

  try {
    const resp = await DocumentsService.getPreviewUrl(jobId);
    renderPreview(_previewPanel, {
      url: resp.url,
      contentType,
      watermarkEmail: Session.getEmail() || "",
    });
  } catch {
    _previewPanel.innerHTML = '<p class="empty-state">Preview unavailable</p>';
    _previewPanel.classList.remove("watermarked", "watermark-block");
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
      ["BDA Time", doc.bdaProcessingTimeSeconds != null ? `${doc.bdaProcessingTimeSeconds}s` : "-"],
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
  _detailContent.innerHTML = sections.join("");

  _collapseBtn.classList.remove("disabled");
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
