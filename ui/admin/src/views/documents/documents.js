import * as DocumentsService from "../../services/documents.js";
import * as Helpers from "../../utils/helpers.js";
import * as Toast from "../../utils/toast.js";
import * as Session from "../../utils/session.js";
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
const STORAGE_KEY_SEARCHES = "docai_documents_searches";

// Saved searches are stored as lightweight row objects (jobId, fileName,
// processStatus, createdAt) so the sidebar can be rebuilt without re-fetching
// each document - which would otherwise log a view/search audit event per row.
function _getSavedSearches() {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(STORAGE_KEY_SEARCHES)) || [];
    // Tolerate the legacy bare-string format from earlier sessions.
    return parsed.filter((row) => row && typeof row === "object" && row.jobId);
  } catch {
    return [];
  }
}

function _saveSearch(row) {
  const searches = _getSavedSearches().filter((r) => r.jobId !== row.jobId);
  searches.unshift(row);
  sessionStorage.setItem(STORAGE_KEY_SEARCHES, JSON.stringify(searches.slice(0, 20)));
}

let _root, _listEl, _noDocuments;
let _searchInput, _searchBtn, _detailPanel, _previewPanel, _detailContent, _collapseBtn;
let _activeJobId = null;
let _detailCollapsed = true;
let _fieldGeometry = null;
let _resizeObserver = null;

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  Helpers.setViewActions(); // no header actions for this view

  _searchInput = root.querySelector("#document-search-input");
  _searchBtn = root.querySelector("#document-search-btn");
  _listEl = root.querySelector("#documents-list");
  _noDocuments = root.querySelector("#no-documents");
  _detailPanel = root.querySelector("#document-detail-panel");
  _previewPanel = root.querySelector("#document-preview-panel");
  _detailContent = root.querySelector("#detail-content");
  _collapseBtn = root.querySelector("#detail-collapse-btn");

  _collapseBtn.addEventListener("click", toggleDetailPanel);
  _collapseBtn.classList.add("disabled");

  // Hovering a field row highlights its bbox in the preview. Delegated on the
  // containers, so it survives detail/table re-renders and async overlay render.
  linkFieldHighlighting(_detailContent, _previewPanel);

  _searchBtn.disabled = true;
  _searchInput.addEventListener("input", () => {
    _searchBtn.disabled = !_searchInput.value.trim();
  });
  _searchBtn.addEventListener("click", handleSearch);
  _searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && _searchInput.value.trim()) handleSearch();
  });

  load();
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
  // Nothing to show -> the collapse toggle has no purpose.
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
  _listEl.innerHTML = "";

  // Rebuild the sidebar from cached row data - no document fetch, so no audit
  // event is logged for merely repopulating the list. Detail/preview (and their
  // audit events) only fire when a document is actually opened below.
  for (const row of _getSavedSearches()) {
    _listEl.appendChild(buildListItem(row));
  }

  if (!_listEl.children.length) {
    _noDocuments.textContent = "Search for a document by Job ID";
    _noDocuments.classList.remove("hidden");
  } else {
    _noDocuments.classList.add("hidden");
  }

  // Restore active document
  const savedActive = sessionStorage.getItem(STORAGE_KEY_ACTIVE);
  if (savedActive) {
    _activeJobId = savedActive;
    const el = _listEl.querySelector(`[data-job-id="${savedActive}"]`);
    if (el) el.classList.add("active");
    loadDetail(savedActive);
  }
}

async function handleSearch() {
  const query = _searchInput.value.trim();
  if (!query) return;

  try {
    const detail = await DocumentsService.get(query);
    // Add to top of list if not already present
    const existing = _listEl.querySelector(`[data-job-id="${detail.jobId}"]`);
    if (existing) {
      _listEl.querySelectorAll(".doc-list-item").forEach((el) => el.classList.remove("active"));
      existing.classList.add("active");
    } else {
      _listEl.querySelectorAll(".doc-list-item").forEach((el) => el.classList.remove("active"));
      const li = buildListItem({
        jobId: detail.jobId,
        fileName: detail.fileName,
        processStatus: detail.processStatus,
        createdAt: detail.createdAt,
      });
      li.classList.add("active");
      _listEl.prepend(li);
      _noDocuments.classList.add("hidden");
    }
    _activeJobId = detail.jobId;
    sessionStorage.setItem(STORAGE_KEY_ACTIVE, detail.jobId);
    _saveSearch({
      jobId: detail.jobId,
      fileName: detail.fileName,
      processStatus: detail.processStatus,
      createdAt: detail.createdAt,
    });
    renderDetail(detail);
    expandDetailPanel();
    loadPreview(detail.jobId, detail.contentType);
  } catch (e) {
    if (e.status === 404) {
      Toast.show("Document not found");
    } else {
      Toast.show(`Search failed: ${e.message}`);
    }
  }
}

function buildListItem(doc) {
  const cls =
    doc.processStatus === "completed"
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

function renderList(documents) {
  _listEl.innerHTML = "";
  if (documents.length === 0) {
    _noDocuments.textContent = "No documents yet";
    _noDocuments.classList.remove("hidden");
    return;
  }
  _noDocuments.classList.add("hidden");
  for (const doc of documents) {
    _listEl.appendChild(buildListItem(doc));
  }
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
    const detail = await DocumentsService.get(jobId);
    renderDetail(detail);
    expandDetailPanel();
    loadPreview(jobId, detail.contentType);
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
    sections.push(renderExtractedData(doc.fields));
  }

  // eslint-disable-next-line no-unsanitized/property -- server data rendered with esc()
  _detailContent.innerHTML = sections.join("");

  // There's content now, so the collapse toggle is usable.
  _collapseBtn.classList.remove("disabled");

  bindExtractedDataToggle();
}

function bindExtractedDataToggle() {
  const toggle = _detailContent.querySelector(".extracted-data-toggle");
  if (toggle) {
    toggle.addEventListener("change", async () => {
      if (toggle.checked) {
        try {
          const detail = await DocumentsService.get(_activeJobId, {
            includeExtractedData: true,
            includeBoundingBox: true,
          });
          if (detail.fields) {
            _fieldGeometry = extractGeometry(detail.fields);
            const table = _detailContent.querySelector(".extracted-data-table");
            // eslint-disable-next-line no-unsanitized/property -- rendered with esc()
            if (table) table.outerHTML = renderExtractedData(detail.fields, { revealed: true });
            bindExtractedDataToggle();
            if (_resizeObserver) _resizeObserver.disconnect();
            _resizeObserver = renderBboxOverlay(_previewPanel, _fieldGeometry);
            markFieldsWithGeometry(_detailContent, _fieldGeometry);
          }
        } catch (e) {
          Toast.show(`Failed to load extracted data: ${e.message}`);
          toggle.checked = false;
        }
      } else {
        _detailContent.querySelectorAll(".extracted-value").forEach((td) => {
          td.textContent = "\u2022\u2022\u2022\u2022\u2022";
        });
        clearBboxOverlay(_previewPanel);
        if (_resizeObserver) {
          _resizeObserver.disconnect();
          _resizeObserver = null;
        }
        _fieldGeometry = null;
        markFieldsWithGeometry(_detailContent, null);
      }
    });
  }
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
  // Section name is the table's own <thead> header (styled by the global `th`
  // rule), so it reads as part of the table like the API keys table.
  return `<table class="detail-table"><thead><tr><th colspan="2">${Helpers.esc(title)}</th></tr></thead><tbody>${rows}</tbody></table>`;
}
