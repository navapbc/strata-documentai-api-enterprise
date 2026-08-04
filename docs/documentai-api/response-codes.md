# Response Codes

Every processed document result includes a `responseCode` field. Codes are grouped by range.

## 0xx - Success

| Code | Name | Description |
|------|------|-------------|
| `000` | Success | Document processed successfully. All required fields extracted. |
| `002` | No blueprint matched | Document reached BDA but no configured blueprint matched the document type. |
| `003` | AI consent declined | Document not processed - AI consent was not provided. |
| `004` | Processing excluded | Document excluded by sampling configuration for the tenant/category. |
| `005` | Skipped per preclassification | Preclassification returned `other_document` and `SKIP_BDA_IF_UNCLASSIFIED` is enabled. |

## 1xx - Extraction issues

| Code | Name | Description |
|------|------|-------------|
| `101` | Missing fields | One or more required fields were not found or fell below the confidence threshold. |
| `102` | Miscategorized | Document type does not match the category specified at upload. |
| `103` | No document detected | No readable document found in the file. |
| `104` | Blurry document | Document failed blur detection. Only set when `ENFORCE_BLUR_REJECTION` is enabled. |
| `105` | Low extraction confidence | Average field confidence is below the tenant-configured threshold. |
| `106` | Password protected | Document is password-protected and could not be processed. |

## 4xx - Document structure

| Code | Name | Description |
|------|------|-------------|
| `400` | Multiple documents on single page | Preclassification detected more than one distinct document on a single page. |
| `401` | Multiple documents in multipage | Multipage document contains pages that are not continuations of a single document instance (e.g. two different pay stubs, or mixed document types). Only set when `FLAG_MULTIPLE_DOCUMENTS_IN_MULTIPAGE` is enabled. _Detection is best-effort for same-type/different-individual cases (e.g. two pay stubs for different employees) - false negatives are possible; the document will proceed to normal extraction._ |

## 9xx - Errors

| Code | Name | Description |
|------|------|-------------|
| `999` | Internal processing error | Unexpected error during processing. |
