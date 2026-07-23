# Per-Category Document Processing Sampling

- Status: accepted
- Date: 2026-07-23

## Context and Problem Statement

Document extraction has a cost per document. Not every tenant needs 100% of uploaded documents to go through the full extraction pipeline - some want to process a representative sample for auditing, cost control, or gradual rollout. How should sampling be controlled?

## Considered Options

- **Tenant-level sampling** - a single percentage applied to all documents for a tenant
- **Per-category sampling** - a percentage per document category per tenant
- **No sampling** - process everything, leave cost control to the tenant's upload behavior

## Decision Outcome

Chosen option: per-category sampling, because different document types have different processing value and cost profiles. A tenant may want 100% of identity documents processed but only 20% of receipts.

The `processingPercentage` field (0.0-1.0) is stored on the document category record and checked in the document processor before the document enters the document extraction pipeline. Documents that fail the sampling check are marked `PROCESSING_EXCLUDED` - a terminal status treated as completed but not successful.

Sampling is applied immediately after the password-protection check, before blur detection and preclassification. Excluded documents incur no blur-detection or LLM preclassification cost. Password-protected documents are not subject to sampling — they are already terminal and unprocessable regardless of category.

## Pros and Cons of the Options

### Tenant-level sampling

- Good, because simpler to configure
- Bad, because a single rate cannot reflect the different value of different document types

### Per-category sampling (chosen)

- Good, because tenants can tune sampling independently per document type
- Good, because the category record is already the right place for per-category processing config
- Bad, because slightly more configuration surface area for tenants to manage

### No sampling

- Good, because no added complexity
- Bad, because tenants have no cost control mechanism short of not uploading documents
