import * as DocumentsService from "../services/documents.js";
import * as TenantContext from "../utils/tenant-context.js";
import * as Helpers from "../utils/helpers.js";
import * as Toast from "../utils/toast.js";
import { h } from "../utils/dom.js";
import { tpl } from "../utils/tpl.js";
import html from "./documents.html";

const tmpl = tpl(html);

let _root, _tbody, _noDocuments, _refreshBtn, _nextBtn, _prevBtn;
let _searchInput, _searchBtn, _detailPanel;
let _cursor = null;
let _cursorStack = [];
let _tenantUnsub = null;

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  // Inject actions into shared header
  _searchInput = h("input", { type: "text", id: "document-search-input", placeholder: "Search by Job ID...", className: "search-input" });
  _searchBtn = h("button", { className: "btn-secondary" }, "Search");
  _refreshBtn = h("button", { className: "btn-secondary" }, "Refresh");
  Helpers.setViewActions(_searchInput, _searchBtn, _refreshBtn);

  _tbody = root.querySelector("#documents-tbody");
  _noDocuments = root.querySelector("#no-documents");
  _nextBtn = root.querySelector("#documents-next-btn");
  _prevBtn = root.querySelector("#documents-prev-btn");
  _detailPanel = root.querySelector("#document-detail-panel");

  _refreshBtn.addEventListener("click", () => {
    resetPagination();
    load();
  });
  _nextBtn.addEventListener("click", loadNext);
  _prevBtn.addEventListener("click", loadPrev);
  _searchBtn.addEventListener("click", handleSearch);
  _searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleSearch();
  });

  _tenantUnsub = TenantContext.onChange(() => {
    resetPagination();
    clearDetail();
    load();
  });
  load();
}

export function unmount(root) {
  if (_tenantUnsub) {
    _tenantUnsub();
    _tenantUnsub = null;
  }
  root.replaceChildren();
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

  Helpers.showLoading(_tbody, _noDocuments);

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
    const cls =
      doc.processStatus === "completed"
        ? "badge-success"
        : doc.processStatus === "failed"
          ? "badge-danger"
          : "badge-neutral";
    const tr = h(
      "tr",
      { className: "clickable-row" },
      h("td", null, doc.fileName || "—"),
      h("td", null, h("code", null, doc.jobId?.slice(0, 8) || "—")),
      h(
        "td",
        null,
        doc.processStatus
          ? h("span", { className: `badge ${cls}` }, doc.processStatus)
          : document.createTextNode("—"),
      ),
      h("td", null, doc.documentCategory || "—"),
      h("td", null, doc.matchedBlueprint || "—"),
      h("td", null, Helpers.formatDate(doc.createdAt)),
    );
    tr.addEventListener("click", () => loadDetail(doc.jobId));
    _tbody.appendChild(tr);
  }
}

async function loadDetail(jobId) {
  _detailPanel.textContent = "Loading...";
  try {
    const detail = await DocumentsService.get(jobId);
    renderDetail(detail);
  } catch (e) {
    _detailPanel.textContent = e.message;
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
          : "—",
      ],
      ["Document Class", doc.matchedDocumentClass],
    ]),
    renderSection("Processing", [
      ["Created", doc.createdAt],
      ["Processed", doc.processedDate],
      [
        "Total Time",
        doc.totalProcessingTimeSeconds != null ? `${doc.totalProcessingTimeSeconds}s` : "—",
      ],
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

  // eslint-disable-next-line no-unsanitized/property -- server data rendered with esc()
  _detailPanel.innerHTML = sections.join("");
}

function renderSection(title, fields) {
  const rows = fields
    .filter(([, val]) => val != null && val !== "" && val !== "—")
    .map(
      ([label, val]) =>
        `<tr><td class="detail-label">${Helpers.esc(label)}</td><td>${Helpers.esc(String(val))}</td></tr>`,
    )
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
      const cls =
        score >= 0.9 ? "confidence-high" : score >= 0.7 ? "confidence-med" : "confidence-low";
      return `<tr><td class="detail-label">${Helpers.esc(field)}</td><td class="${cls}">${pct}%</td></tr>`;
    })
    .join("");
  return `<h4>Field Confidence</h4><table class="detail-table"><tbody>${rows}</tbody></table>`;
}
