import * as DocumentsService from "../../services/documents.js";
import * as TenantContext from "../../utils/tenant-context.js";
import * as Helpers from "../../utils/helpers.js";
import * as Toast from "../../utils/toast.js";
import { h } from "../../utils/dom.js";
import { tpl } from "../../utils/tpl.js";
import html from "./documents.html";

const tmpl = tpl(html);

let _root, _listEl, _noDocuments;
let _searchInput, _searchBtn, _detailPanel;
let _activeJobId = null;
let _tenantUnsub = null;

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  Helpers.setViewActions(); // no header actions for this view

  _searchInput = root.querySelector("#document-search-input");
  _searchBtn = root.querySelector("#document-search-btn");
  _listEl = root.querySelector("#documents-list");
  _noDocuments = root.querySelector("#no-documents");
  _detailPanel = root.querySelector("#document-detail-panel");

  _searchBtn.disabled = true;
  _searchInput.addEventListener("input", () => {
    _searchBtn.disabled = !_searchInput.value.trim();
  });
  _searchBtn.addEventListener("click", handleSearch);
  _searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && _searchInput.value.trim()) handleSearch();
  });

  _tenantUnsub = TenantContext.onChange(() => {
    clearDetail();
    _activeJobId = null;
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

function clearDetail() {
  _detailPanel.replaceChildren();
}

export async function load() {
  const tenantId = TenantContext.getTenantId();
  if (!tenantId) {
    _listEl.innerHTML = "";
    _noDocuments.textContent = "Select a tenant to view documents.";
    _noDocuments.classList.remove("hidden");
    return;
  }

  _noDocuments.classList.add("hidden");
  _listEl.innerHTML = '<li class="doc-list-item doc-list-loading">Loading…</li>';

  try {
    const resp = await DocumentsService.list({ tenantId, limit: 50 });
    renderList(resp.documents || []);
  } catch (e) {
    _listEl.innerHTML = "";
    _noDocuments.textContent = e.message;
    _noDocuments.classList.remove("hidden");
  }
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

function renderList(documents) {
  _listEl.innerHTML = "";
  if (documents.length === 0) {
    _noDocuments.textContent = "No documents yet";
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
    const badge = doc.processStatus
      ? h("span", { className: `badge ${cls}` }, doc.processStatus)
      : null;
    const li = h(
      "li",
      { className: `doc-list-item${doc.jobId === _activeJobId ? " active" : ""}` },
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
    _listEl.appendChild(li);
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

  if (doc.fieldConfidenceScores && Object.keys(doc.fieldConfidenceScores).length > 0) {
    sections.push(renderConfidenceScores(doc.fieldConfidenceScores));
  }

  // eslint-disable-next-line no-unsanitized/property -- server data rendered with esc()
  _detailPanel.innerHTML = sections.join("");
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
  return `<h4>${Helpers.esc(title)}</h4><table class="detail-table"><tbody>${rows}</tbody></table>`;
}

function renderExtractedData(data) {
  if (typeof data !== "object" || data === null) return "";
  const rows = Object.entries(data)
    .map(([key, val]) => {
      const display = typeof val === "object" ? JSON.stringify(val) : String(val ?? "-");
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
