/**
 * Document metadata sections (Overview / Tenant / Classification / Processing)
 * shared by the admin document pane and the demo results panel. Styles live in
 * shared/styles/document-detail.css.
 */

import {
  esc,
  formatFileSize,
  EXTRACTION_METHOD_LABELS,
} from "../utils/helpers.js";
import { formatDateTime } from "../utils/dates.js";
import { MASKED_VALUE } from "../utils/presentation-mode.js";

/**
 * Render one titled key/value table. Rows with an empty value are dropped and
 * a section with no rows renders as "".
 * @param {string} title
 * @param {Array<[string, unknown]>} fields - [label, value] pairs
 * @returns {string} HTML string (all values escaped)
 */
export function renderDetailSection(title, fields) {
  const rows = fields
    .filter(([, val]) => val != null && val !== "" && val !== "-")
    .map(
      ([label, val]) =>
        `<tr><td class="detail-label">${esc(label)}</td><td>${esc(String(val))}</td></tr>`,
    )
    .join("");
  if (!rows) {
    return "";
  }
  return `<table class="detail-table detail-section"><thead><tr><th colspan="2">${esc(title)}</th></tr></thead><tbody>${rows}</tbody></table>`;
}

/**
 * Render the document metadata sections (Overview, Tenant, Classification,
 * Processing) shared by the admin document pane and the demo results panel.
 * @param {Object} doc - DocumentDetail API response
 * @param {object} [opts]
 * @param {boolean} [opts.showTenant=true] - include the Tenant section
 * @param {boolean} [opts.presented=false] - mask tenant / class (presentation mode)
 * @returns {string[]} HTML strings, one per section ("" for empty sections)
 */
export function renderDocumentDetailSections(
  doc,
  { showTenant = true, presented = false } = {},
) {
  const seconds = (val) => (val != null ? `${val}s` : null);
  return [
    renderDetailSection("Overview", [
      ["File Name", doc.fileName],
      ["Content Type", doc.contentType],
      ["Pages", doc.pagesDetected],
      ["Size", formatFileSize(doc.fileSizeBytes)],
      ["External ID", doc.externalDocumentId],
      ["Batch ID", doc.batchId],
      ["Created", formatDateTime(doc.createdAt)],
    ]),
    showTenant
      ? renderDetailSection("Tenant", [
          [
            "Tenant",
            presented ? (doc.maskedTenantId ?? doc.tenantId) : doc.tenantId,
          ],
          ["API Key", presented ? MASKED_VALUE : doc.apiKeyName],
        ])
      : "",
    renderDetailSection("Classification", [
      ["Document Class", presented ? MASKED_VALUE : doc.matchedDocumentClass],
      [
        "Classification Confidence",
        doc.matchedBlueprintConfidence != null
          ? `${(doc.matchedBlueprintConfidence * 100).toFixed(1)}%`
          : null,
      ],
    ]),
    renderDetailSection("Processing", [
      ["Job ID", doc.jobId],
      ["Status", doc.processStatus],
      ["Upload Category", doc.documentCategory],
      ["Total Duration", seconds(doc.totalProcessingTimeSeconds)],
      ["Extraction Duration", seconds(doc.bdaProcessingTimeSeconds)],
      ["Extraction Region", doc.bdaRegionUsed],
      [
        "Extraction Method",
        doc.extractionMethod
          ? (EXTRACTION_METHOD_LABELS[doc.extractionMethod] ??
            doc.extractionMethod)
          : null,
      ],
      ["Retries", doc.retryCount],
      ["Error", doc.errorMessage],
    ]),
  ];
}
