# Defer the Document/Job Identity Split; Start Collecting `systemDocumentId` Now

- Status: accepted
- Date: 2026-08-14

## Context and Problem Statement

`GET /v1/documents/{job_id}` (and its sibling `DELETE`) key the documents collection by `job_id`, not a document id. This is semantically incorrect and should be rectified.

The endpoint is potentially confusing, but not yet an "issue", as a single uploaded document can have exactly one invocation. The mismatch will become a problem once a single uploaded document can have more than one processing run - e.g. a dual-engine shadow comparison, or reprocessing after a blueprint/model change. Neither exist today as engine selection is mutually exclusive per document - `job_id` and document are still strictly 1:1.

## Decision Drivers

- This incorrect semantics observation has surfaced multiple times and will likely do so again
- Do not ship client-visible deprecation signals when no immediate need exists
- Providing an explicit distinction between jobs and documents is a necessary step

## Considered Options

- **Leave `job_id` as the sole identifier, revisit only when the trigger fires** - no code change required
- **Migrate the resource model now**: new `/v1/documents/{document_id}` endpoint, `job_id` path deprecated, GSI + lookup path for the new id
- **Write `systemDocumentId` now (mirrors `job_id`), defer everything else** - no new endpoint, no GSI, no deprecation of the current path

## Decision Outcome

Chosen option: write `systemDocumentId` now, defer the remainder. Every document write path (`/v1/documents`, `/wait`, batch, build, presigned) sets `systemDocumentId = job_id` on the DDB record. No GSI, no query path, no new route, and the existing `job_id`-keyed endpoints are untouched.

**Trigger condition to revisit this ADR:** a document gains a second processing run (dual-engine shadow/compare, or reprocessing). At that point, decide `document_id` identity semantics, add the GSI and lookup, and migrate the endpoint - either promote `document_id` to the existing path with `job_id` kept as a thin alias, or a deliberate `/jobs/{id}` split moving all run-scoped endpoints (status, evaluation) together. Do not ship a lone divergent endpoint under an inconsistent scheme.

## Pros and Cons of the Options

### Leave `job_id` as-is, revisit later

- Good, because zero code to maintain until the requirement is real
- Bad, because it requires a backfill migration once the trigger fires - every record created before that point lacks a document id

### Migrate the resource model now

- Bad, because `document_id` identity semantics aren't answerable yet - nothing forces "what counts as the same document"
- Bad, because it deprecates a live endpoint in favor of one that doesn't exist, which is what the reverted first attempt did
- Bad, because it provisions a GSI with no query path using it

### Write `systemDocumentId` now, defer the rest (chosen)

- Good, because new records are backfill-free once the real migration happens
- Good, because it costs nothing today: no index, no new route, no deprecation of a live path
- Bad, because the field is inert until the trigger fires - a future reader could reasonably ask why it duplicates `job_id`
