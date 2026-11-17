# Preclassification

Before a document reaches BDA for extraction, the platform runs preclassification using a Bedrock vision model to inspect the document. The model determines the document type, whether it contains multiple documents, whether a multipage PDF is internally consistent, and which BDA blueprint it should be routed to. Supports PDF, JPEG, PNG, GIF, and WebP; images over 5MB are skipped. Preclassification runs in the document processor Lambda, concurrently with blur detection and bounding-box detection.

![Preclassification pipeline](media/preclassification.svg)

## Two parallel AWS Bedrock calls

Both calls run in parallel using the same model (`us.amazon.nova-pro-v1:0` by default, overridable via SSM).

**`preclassify_document`** sends the document with a structured prompt and returns:

| Field | Description |
|---|---|
| `document_type` | Short free-text description of the document |
| `confidence` | 0.0–1.0 |
| `max_document_count_on_page` | Highest number of distinct documents visible on any single page |
| `has_multipage_inconsistency` | True if pages appear to belong to different document instances or individuals |
| `category_match` | Whether the document matches the `user_category` provided at upload |
| `is_identity_document` | True if the document is a passport or driver's license |

**`find_matching_blueprint`** sends the document with a different prompt listing all available BDA blueprint schemas. The model picks the single best match and returns a label and confidence score. A match is accepted only if the label exactly matches a known schema key and confidence is ≥ 0.5. Blueprint matching uses `temperature=0.0` for determinism.

## PDF handling

PDFs are truncated to the first 5 pages before either call, matching BDA's own page limit. The truncated PDF is then compressed for classification: scanned pages with oversized images are rasterized via pypdfium2 at a maximum of 1400px on the longest side; PDFs with no oversized images are passed through unchanged. BDA always receives the original bytes.

`preclassify_document` splits the PDF into 5-page windows and runs each as a separate Bedrock call (up to 8 in parallel). Since the PDF is already truncated to 5 pages, this is always a single call today - the windowing logic exists for cases where the window size is set below the page limit. Results across chunks are merged: `document_type` and `confidence` come from the first chunk; `max_document_count_on_page` is the max; `has_multipage_inconsistency` and `is_identity_document` are true if any chunk flagged them. A failed chunk is treated as clean - transient errors don't block processing. Because classification covers only the first 5 pages, a mixed document where distinct types appear on page 6 or later will not be flagged - see the [ADR](../decisions/2026-11-16-pdf-classification-compression.md) for the tradeoff.

Blueprint matching always uses only the first window since it identifies form type, not cross-page consistency.

## Routing

After both calls complete, these rules are applied in order - first match wins:

| Condition | Outcome |
|---|---|
| `max_document_count_on_page > 1` | `MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE` (response 400) |
| Multipage PDF + `has_multipage_inconsistency` + flag enabled | `MULTIPLE_DOCUMENTS_IN_MULTIPAGE` (response 401) |
| Matched blueprint is on the tenant's disabled list | `BLUEPRINT_DISABLED` |
| `is_identity_document` is true | Routed to Textract AnalyzeID (when `textract-identity-enabled` is enabled) |
| `document_type == "other_document"` + `skip-bda-if-unclassified` is enabled | `EXCLUDED_PER_PRECLASSIFICATION` - not sent to BDA |
| Otherwise | Proceeds to BDA |

## Feature flags

All flags are SSM parameters under `{ssm_prefix}/feature-flags/`, cached for 5 minutes.

| Flag | Default | Effect |
|---|---|---|
| `enable-preclassification-blueprint-matching` | true | Runs `find_matching_blueprint`; drives category-specific BDA routing |
| `skip-bda-if-unclassified` | false | Skips BDA when preclassification returns `other_document` |
| `flag-multiple-documents-in-multipage` | true | Rejects multipage PDFs with inconsistent pages |
| `textract-identity-enabled` | false | Routes identity documents to Textract AnalyzeID instead of BDA |

## Related

- [feature-flags.md](feature-flags.md)
- [blur-detection.md](blur-detection.md)
- [document-processing.md](document-processing.md)
- [ADR: PDF classification compression](../decisions/2026-11-16-pdf-classification-compression.md)
