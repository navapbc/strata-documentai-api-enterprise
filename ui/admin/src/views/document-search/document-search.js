import * as DocumentsService from "../../services/documents.js";
import * as Helpers from "../../utils/helpers.js";
import * as Toast from "../../utils/toast.js";
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
import html from "./document-search.html";

const tmpl = tpl(html);

let _root, _listEl, _noDocuments;
let _searchInput, _searchBtn, _statusFilter;
let _detailPanel, _previewPanel, _detailContent, _collapseBtn;
let _activeJobId = null;
let _detailCollapsed = true;
let _fieldGeometry = null;
let _resizeObserver = null;
let _searchResults = [];

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  Helpers.setViewActions();

  _searchInput = root.querySelector("#document-search-input");
  _searchBtn = root.querySelector("#document-search-btn");
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

  _searchBtn.addEventListener("click", handleSearch);
  _searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleSearch();
  });
  _statusFilter.addEventListener("change", () => renderList());
}

export function unmount(root) {
  if (_resizeObserver) {
    _resizeObserver.disconnect();
    _resizeObserver = null;
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

async function handleSearch() {
  const query = _searchInput.value.trim();
  if (!query) return;

  _listEl.innerHTML = "";
  _noDocuments.textContent = "Searching…";
  _noDocuments.classList.remove("hidden");

  try {
    // If it looks like a UUID/job ID, do a direct lookup
    const isJobId = /^[0-9a-f-]{20,}$/i.test(query);
    if (isJobId) {
      const detail = await DocumentsService.get(query);
      _searchResults = [
        {
          jobId: detail.jobId,
          fileName: detail.fileName,
          processStatus: detail.processStatus,
          createdAt: detail.createdAt,
          contentType: detail.contentType,
        },
      ];
    } else {
      // Filename search - load from API and filter client-side
      const tenantId = TenantContext.getTenantId();
      const resp = await DocumentsService.list({ tenantId, limit: 50 });
      const docs = resp.documents || resp || [];
      _searchResults = docs.filter((d) =>
        (d.fileName || "").toLowerCase().includes(query.toLowerCase()),
      );
    }
  } catch (e) {
    if (e.status === 404) {
      _searchResults = [];
    } else {
      Toast.show(`Search failed: ${e.message}`);
      _searchResults = [];
    }
  }

  renderList();

  // Auto-select if single result
  if (_searchResults.length === 1) {
    const doc = _searchResults[0];
    _activeJobId = doc.jobId;
    const el = _listEl.querySelector(`[data-job-id="${doc.jobId}"]`);
    if (el) el.classList.add("active");
    loadDetail(doc.jobId);
  }
}

function renderList() {
  _listEl.innerHTML = "";
  const statusFilter = _statusFilter?.value || "";
  const filtered = _searchResults.filter((doc) => {
    if (statusFilter && doc.processStatus !== statusFilter) return false;
    return true;
  });

  if (!filtered.length) {
    _noDocuments.textContent = !_searchResults.length
      ? "No results found"
      : "No matching documents";
    _noDocuments.classList.remove("hidden");
    return;
  }

  _noDocuments.classList.add("hidden");
  for (const doc of filtered) {
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
    loadPreview(jobId, detail.contentType);
    if (_fieldGeometry) {
      _resizeObserver = renderBboxOverlay(_previewPanel, _fieldGeometry);
      markFieldsWithGeometry(_detailContent, _fieldGeometry);
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
