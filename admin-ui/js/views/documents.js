import * as DocumentsService from "../services/documents.js";
import * as TenantContext from "../utils/tenant-context.js";
import * as Helpers from "../utils/helpers.js";
import * as Toast from "../utils/toast.js";

let _tbody, _noDocuments, _refreshBtn, _nextBtn, _prevBtn;
let _searchInput, _searchBtn, _detailPanel;
let _cursor = null;
let _cursorStack = [];

export function init() {
  _tbody = document.getElementById("documents-tbody");
  _noDocuments = document.getElementById("no-documents");
  _refreshBtn = document.getElementById("refresh-documents-btn");
  _nextBtn = document.getElementById("documents-next-btn");
  _prevBtn = document.getElementById("documents-prev-btn");
  _searchInput = document.getElementById("document-search-input");
  _searchBtn = document.getElementById("document-search-btn");
  _detailPanel = document.getElementById("document-detail-panel");

  _refreshBtn.addEventListener("click", () => { resetPagination(); load(); });
  _nextBtn.addEventListener("click", loadNext);
  _prevBtn.addEventListener("click", loadPrev);
  _searchBtn.addEventListener("click", handleSearch);
  _searchInput.addEventListener("keydown", (e) => { if (e.key === "Enter") handleSearch(); });

  TenantContext.onChange(() => { resetPagination(); clearDetail(); load(); });
}

function resetPagination() {
  _cursor = null;
  _cursorStack = [];
}

function clearDetail() {
  _detailPanel.innerHTML = '<p class="empty-state">Select a document to view details</p>';
}

export async function load() {
  const tenantId = TenantContext.getTenantId();
  if (!tenantId) {
    _tbody.innerHTML = "";
    _noDocuments.textContent = "Select a tenant to view documents.";
    _noDocuments.classList.remove("hidden");
    _nextBtn.disabled = true;
    _prevBtn.disabled = true;
    return;
  }

  try {
    const resp = await DocumentsService.list({
      tenantId,
      limit: 50,
      cursor: _cursor || undefined,
    });
    renderTable(resp.documents || []);
    _nextBtn.disabled = !resp.nextCursor;
    _nextBtn.dataset.cursor = resp.nextCursor || "";
    _prevBtn.disabled = _cursorStack.length === 0;
  } catch (e) {
    _tbody.innerHTML = "";
    _noDocuments.textContent = e.message;
    _noDocuments.classList.remove("hidden");
  }
}

function loadNext() {
  const next = _nextBtn.dataset.cursor;
  if (!next) return;
  _cursorStack.push(_cursor);
  _cursor = next;
  load();
}

function loadPrev() {
  if (_cursorStack.length === 0) return;
  _cursor = _cursorStack.pop();
  load();
}

async function handleSearch() {
  const query = _searchInput.value.trim();
  if (!query) return;

  try {
    const detail = await DocumentsService.get(query);
    renderDetail(detail);
  } catch (e) {
    if (e.status === 404) {
      Toast.show("Document not found");
    } else {
      Toast.show(`Search failed: ${e.message}`);
    }
  }
}

function renderTable(documents) {
  _tbody.innerHTML = "";
  if (documents.length === 0) {
    _noDocuments.textContent = "No documents found.";
    _noDocuments.classList.remove("hidden");
    return;
  }
  _noDocuments.classList.add("hidden");
  for (const doc of documents) {
    const tr = document.createElement("tr");
    tr.classList.add("clickable-row");
    tr.innerHTML = `
      <td>${Helpers.esc(doc.fileName || "—")}</td>
      <td><code>${Helpers.esc(doc.jobId?.slice(0, 8) || "—")}</code></td>
      <td>${statusBadge(doc.processStatus)}</td>
      <td>${Helpers.esc(doc.documentCategory || "—")}</td>
      <td>${Helpers.esc(doc.matchedBlueprint || "—")}</td>
      <td>${Helpers.formatDate(doc.createdAt)}</td>
    `;
    tr.addEventListener("click", () => loadDetail(doc.jobId));
    _tbody.appendChild(tr);
  }
}

function statusBadge(status) {
  if (!status) return "—";
  const cls = status === "completed" ? "badge-success"
    : status === "failed" ? "badge-danger"
    : "badge-neutral";
  return `<span class="badge ${cls}">${Helpers.esc(status)}</span>`;
}

async function loadDetail(jobId) {
  _detailPanel.innerHTML = '<p class="loading">Loading...</p>';
  try {
    const detail = await DocumentsService.get(jobId);
    renderDetail(detail);
  } catch (e) {
    _detailPanel.innerHTML = `<p class="error">${Helpers.esc(e.message)}</p>`;
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
      ["Blueprint Confidence", doc.matchedBlueprintConfidence != null ? `${(doc.matchedBlueprintConfidence * 100).toFixed(1)}%` : "—"],
      ["Document Class", doc.matchedDocumentClass],
    ]),
    renderSection("Processing", [
      ["Created", doc.createdAt],
      ["Processed", doc.processedDate],
      ["Total Time", doc.totalProcessingTimeSeconds != null ? `${doc.totalProcessingTimeSeconds}s` : "—"],
      ["BDA Time", doc.bdaProcessingTimeSeconds != null ? `${doc.bdaProcessingTimeSeconds}s` : "—"],
      ["BDA Region", doc.bdaRegionUsed],
      ["Retries", doc.retryCount],
      ["Error", doc.errorMessage],
    ]),
    renderSection("File", [
      ["Content Type", doc.contentType],
      ["Size", doc.fileSizeBytes != null ? `${(doc.fileSizeBytes / 1024).toFixed(1)} KB` : "—"],
      ["Pages", doc.pagesDetected],
    ]),
  ];

  if (doc.fields) {
    sections.push(renderExtractedData(doc.fields));
  }

  if (doc.fieldConfidenceScores && Object.keys(doc.fieldConfidenceScores).length > 0) {
    sections.push(renderConfidenceScores(doc.fieldConfidenceScores));
  }

  _detailPanel.innerHTML = sections.join("");
}

function renderSection(title, fields) {
  const rows = fields
    .filter(([, val]) => val != null && val !== "" && val !== "—")
    .map(([label, val]) => `<tr><td class="detail-label">${Helpers.esc(label)}</td><td>${Helpers.esc(String(val))}</td></tr>`)
    .join("");
  if (!rows) return "";
  return `<h4>${Helpers.esc(title)}</h4><table class="detail-table"><tbody>${rows}</tbody></table>`;
}

function renderExtractedData(data) {
  if (typeof data !== "object" || data === null) return "";
  const rows = Object.entries(data)
    .map(([key, val]) => {
      const display = typeof val === "object" ? JSON.stringify(val) : String(val ?? "—");
      return `<tr><td class="detail-label">${Helpers.esc(key)}</td><td>${Helpers.esc(display)}</td></tr>`;
    })
    .join("");
  return `<h4>Extracted Data</h4><table class="detail-table"><tbody>${rows}</tbody></table>`;
}

function renderConfidenceScores(scores) {
  const rows = Object.entries(scores)
    .sort(([, a], [, b]) => a - b)
    .map(([field, score]) => {
      const pct = (score * 100).toFixed(1);
      const cls = score >= 0.9 ? "confidence-high" : score >= 0.7 ? "confidence-med" : "confidence-low";
      return `<tr><td class="detail-label">${Helpers.esc(field)}</td><td class="${cls}">${pct}%</td></tr>`;
    })
    .join("");
  return `<h4>Field Confidence</h4><table class="detail-table"><tbody>${rows}</tbody></table>`;
}
