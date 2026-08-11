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
let _statusFilter, _detailPanel, _previewPanel, _detailContent;
let _activeJobId = null;
let _fieldGeometry = null;
let _resizeObserver = null;
let _unsubTenant = null;
let _recentDocuments = [];

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  Helpers.setViewActions();

  _activeJobId = null;
  _fieldGeometry = null;
  _resizeObserver = null;
  _recentDocuments = [];

  _statusFilter = root.querySelector("#document-status-filter");
  _listEl = root.querySelector("#documents-list");
  _noDocuments = root.querySelector("#no-documents");
  _detailPanel = root.querySelector("#document-detail-panel");
  _previewPanel = root.querySelector("#document-preview-panel");
  _detailContent = root.querySelector("#detail-content");

  linkFieldHighlighting(_detailContent, _previewPanel);

  _statusFilter.addEventListener("change", () => load());

  TenantContext.mountSelect(root.querySelector("#tenant-select"), { placeholder: "Select Tenant" });
  _unsubTenant = TenantContext.onChange(() => {
    _activeJobId = null;
    sessionStorage.removeItem(STORAGE_KEY_ACTIVE);
    clearDetail();
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
  const tenantSelect = root.querySelector("#tenant-select");
  if (tenantSelect) TenantContext.unmountSelect(tenantSelect);
  root.replaceChildren();
}

function clearDetail() {
  _detailContent.innerHTML = "";
  _previewPanel.innerHTML = '<p class="empty-state">Select a document to preview</p>';
  _previewPanel.classList.remove("watermarked", "watermark-block");
}

function showNoDocuments(msg) {
  if (_noDocuments) {
    _noDocuments.textContent = msg;
    _noDocuments.classList.remove("hidden");
  }
}

function hideNoDocuments() {
  if (_noDocuments) _noDocuments.classList.add("hidden");
}

export async function load() {
  const tenantId = TenantContext.getTenantId() || undefined;

  if (!tenantId) {
    _recentDocuments = [];
    _listEl.innerHTML = "";
    _previewPanel.innerHTML = '<p class="empty-state">Select a document to preview</p>';
    showNoDocuments("Select a tenant to view recent documents");
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
  } else if (_recentDocuments.length) {
    const first = _recentDocuments[0];
    _activeJobId = first.jobId;
    sessionStorage.setItem(STORAGE_KEY_ACTIVE, first.jobId);
    _listEl.querySelector(`[data-job-id="${first.jobId}"]`)?.classList.add("active");
    loadDetail(first.jobId);
  }
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

function renderList() {
  _listEl.innerHTML = "";

  if (!_recentDocuments.length) {
    _previewPanel.innerHTML = '<p class="empty-state">Select a document to preview</p>';
    showNoDocuments("No documents found");
    return;
  }

  hideNoDocuments();
  _previewPanel.innerHTML = "";
  const groups = groupByDate(_recentDocuments);
  for (const [label, docs] of groups) {
    const heading = h("li", { className: "doc-list-heading metrics-timeframe-label" }, label);
    _listEl.appendChild(heading);
    for (const doc of docs) {
      _listEl.appendChild(buildListItem(doc));
    }
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
    h("div", { className: "doc-list-meta" }, ...(badge ? [badge] : [])),
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
    await loadPreview(jobId, detail.contentType, detail.processStatus);
    if (_fieldGeometry) {
      _resizeObserver = renderBboxOverlay(_previewPanel, _fieldGeometry);
      markFieldsWithGeometry(_detailContent, _fieldGeometry);
    } else {
      // Some extraction methods (e.g. Textract AnalyzeID) don't return geometry -
      // this is expected, not a bug.
      const note = _detailContent.querySelector(".bbox-unavailable-note");
      if (!note) {
        const p = document.createElement("p");
        p.className = "bbox-unavailable-note empty-state";
        p.textContent = "Bounding box data is not available for this document.";
        _detailContent.appendChild(p);
      }
    }
  } catch (e) {
    _detailContent.textContent = e.message;
  }
}

async function loadPreview(jobId, contentType, processStatus) {
  if (processStatus === "password_protected") {
    _previewPanel.innerHTML =
      '<p class="empty-state">Preview unavailable - document is password protected</p>';
    return;
  }
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
