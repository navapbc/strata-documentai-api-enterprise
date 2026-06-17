import * as DocumentsService from "../../services/documents.js";
import * as TenantContext from "../../utils/tenant-context.js";
import * as Helpers from "../../utils/helpers.js";
import * as Toast from "../../utils/toast.js";
import { h } from "../../utils/dom.js";
import { tpl } from "../../utils/tpl.js";
import html from "./documents.html";

const tmpl = tpl(html);

let _root, _listEl, _noDocuments;
let _searchInput, _searchBtn, _detailPanel, _previewPanel, _detailContent, _collapseBtn;
let _activeJobId = null;
let _detailCollapsed = true;
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
  _previewPanel = root.querySelector("#document-preview-panel");
  _detailContent = root.querySelector("#detail-content");
  _collapseBtn = root.querySelector("#detail-collapse-btn");

  _collapseBtn.addEventListener("click", toggleDetailPanel);
  _collapseBtn.classList.add("disabled");

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
  const previewable = ["application/pdf", "image/jpeg", "image/png"];
  if (!previewable.includes(contentType)) {
    _previewPanel.innerHTML = '<p class="empty-state">Preview not available for this file type</p>';
    return;
  }

  _previewPanel.innerHTML = '<p class="empty-state">Loading preview…</p>';

  try {
    const resp = await DocumentsService.getPreviewUrl(jobId);
    if (contentType === "application/pdf") {
      // eslint-disable-next-line no-unsanitized/property -- URL escaped with esc()
      _previewPanel.innerHTML = `<object data="${Helpers.esc(resp.url)}" type="application/pdf" class="document-preview-frame"><p>Unable to display PDF. <a href="${Helpers.esc(resp.url)}" target="_blank" rel="noopener">Open in new tab</a></p></object>`;
    } else {
      // eslint-disable-next-line no-unsanitized/property -- URL escaped with esc()
      _previewPanel.innerHTML = `<img src="${Helpers.esc(resp.url)}" class="document-preview-img" alt="Document preview" onerror="this.parentElement.innerHTML='<p class=empty-state>Preview unavailable</p>'" />`;
    }
  } catch {
    _previewPanel.innerHTML = '<p class="empty-state">Preview unavailable</p>';
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
          const detail = await DocumentsService.get(_activeJobId, { includeExtractedData: true });
          if (detail.fields) {
            const table = _detailContent.querySelector(".extracted-data-table");
            // eslint-disable-next-line no-unsanitized/property -- rendered with esc()
            if (table) table.outerHTML = renderExtractedData(detail.fields, true);
            bindExtractedDataToggle();
          }
        } catch (e) {
          Toast.show(`Failed to load extracted data: ${e.message}`);
          toggle.checked = false;
        }
      } else {
        _detailContent.querySelectorAll(".extracted-value").forEach((td) => {
          td.textContent = "\u2022\u2022\u2022\u2022\u2022";
        });
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

function renderExtractedData(data, revealed = false) {
  if (typeof data !== "object" || data === null) return "";
  const rows = Object.entries(data)
    .map(([key, val]) => {
      const isObj = val != null && typeof val === "object" && !Array.isArray(val);
      const conf = isObj && typeof val.confidence === "number" ? val.confidence : null;
      const value = isObj && "value" in val ? val.value : val;
      const display =
        value != null && typeof value === "object" ? JSON.stringify(value) : String(value ?? "-");
      return { key, conf, display };
    })
    .sort((a, b) => {
      if (a.conf == null) return b.conf == null ? 0 : 1;
      if (b.conf == null) return -1;
      return a.conf - b.conf;
    })
    .map(({ key, conf, display }) => {
      const confCell =
        conf == null
          ? "<td>-</td>"
          : `<td class="${
              conf >= 0.9 ? "confidence-high" : conf >= 0.7 ? "confidence-med" : "confidence-low"
            }">${(conf * 100).toFixed(1)}%</td>`;
      const valueContent = revealed ? Helpers.esc(display) : "\u2022\u2022\u2022\u2022\u2022";
      return `<tr><td class="detail-label">${Helpers.esc(key)}</td><td class="extracted-value" data-value="${Helpers.esc(display)}">${valueContent}</td>${confCell}</tr>`;
    })
    .join("");
  if (!rows) return "";
  const checked = revealed ? " checked" : "";
  return `<table class="extracted-data-table"><colgroup><col class="ed-col-field"><col class="ed-col-value"><col class="ed-col-conf"></colgroup><thead><tr><th>Extracted Data</th><th colspan="2" class="extracted-data-toggle-cell"><label class="inline-checkbox"><input type="checkbox" class="extracted-data-toggle"${checked}> Show values</label></th></tr><tr><th>Field</th><th>Value</th><th>Confidence</th></tr></thead><tbody>${rows}</tbody></table>`;
}
