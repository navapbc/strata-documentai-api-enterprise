# Preload BDA Blueprint Schemas Instead of Fetching Them at Request Time

- Status: accepted
- Date: 2026-08-25

## Context and Problem Statement

`/v1/dictionary/schemas` and `/v1/dictionary/fields` list document types and fields derived from BDA blueprints across per-category BDA projects. The original implementation invoked BDA's `GetDataAutomationProject`/`GetBlueprint` live on every cache-miss request, with the result held in an in-memory TTL cache per Lambda instance.

With the implementation of category-specific BDA projects (14 projects at time of writing), the live-fetch, per-project approach resulted in BDA throwing multiple `ThrottlingException` exceptions. The issue persisted after capping concurrency to 3 workers down from 14 (1 worker per project). Additionally, fetching in real-time was noticeably slow, regardless of approach (fetching the "all" project, or fetching and combining individual projects).

## Decision Drivers

- BDA's `GetBlueprint`/`GetDataAutomationProject` rate limit is low enough that a handful of concurrent requests trigger it.
- Blueprint schemas rarely change - only when a document type is added/removed under `infra/document-types/`, or an existing custom blueprint's fields are edited (AWS may also update one of their managed blueprint schemas).
- A throttled category's failure was logged as an error, but never surfaced to the API response - callers received a 200 OK with a silently incomplete list, indistinguishable from a correct one.

## Considered Options

- **Live fetch with TTL cache** (original) - call BDA on every cache-miss, cache the result in-process for 60 minutes.
- **Live fetch with tuned concurrency/retries** - reduce concurrency and/or configure boto3 adaptive retry mode to survive throttling.
- **Preload from BDA offline into a static file** (chosen) - fetch once via a CLI, commit the result, read it at runtime with no BDA calls at all.

## Decision Outcome

Chosen option: preload offline into a static file, as blueprint schemas are effectively static data; decouple "collect from BDA" (infrequent, tolerant of latency/throttling) from "serve to callers" (frequent, latency-sensitive) to remove the runtime throttling risk entirely rather than trying to survive it.

A new CLI, `pull-blueprint-schemas` (`make pull-blueprint-schemas`), fetches all category projects' blueprint schemas from BDA and writes them to `documentai-api/src/documentai_api/config/blueprint_schemas.json` - a single file, committed to the repo, and bundled into the Lambda image the same way `config/field_labels/*.json` already is. `get_all_schemas()` reads and parses that file (cached in-process via `lru_cache`) instead of calling BDA. The underlying BDA-fetching functions (`fetch_schemas_from_bda`, `_fetch_project_schemas`) are unchanged and still used by the CLI and by an integration test that validates them directly against real BDA.

`blueprint_arn` was dropped from the schema shape entirely rather than persisted, since custom blueprint ARNs embed the deploying AWS account ID - a per-environment value not appropriate to commit - and nothing internally depended on its value.

### Positive Consequences

- Zero BDA calls, and therefore zero throttling risk, at request time.
- Removes retry/backoff latency variability from `/v1/dictionary/*` requests.
- Fixes the silent-drop bug - a failure during `pull-blueprint-schemas` is a loud CLI error, not a quietly incomplete API response.

### Negative Consequences

- **Staleness**: if AWS changes a managed blueprint's schema on their side, or someone edits a custom blueprint's fields without re-running `pull-blueprint-schemas` and redeploying, the served schema silently drifts from the real BDA blueprint. There is no automatic drift detection today - a stale entry looks identical to a correct one.
- Regenerating the file requires local AWS credentials with BDA read access, `.env` populated via `make env-from-aws`, and a manual `git commit` and redeploy - an extra step easy to forget after a blueprint change.
- This decision covers globally-shared blueprints only, as they exist today. Tenant-authored blueprints are a separate, forthcoming initiative and will need their own design.

## Pros and Cons of the Options

### Live fetch with TTL cache

- Good, because it always reflects the current BDA state with no manual refresh step.
- Bad, because it throttles under realistic concurrency once all category projects are reachable.
- Bad, because a throttled category fails silently, producing an incomplete result with no visible error.

### Live fetch with tuned concurrency/retries

- Good, because it keeps the "always current" property of the original design.
- Bad, because it manages symptoms rather than the cause - the actual BDA rate limit is unknown and may be shared account-wide, so no chosen concurrency/retry setting is provably safe.
- Bad, because adaptive retries trade dropped data for added latency, not a real fix.

### Preload from BDA offline into a static file (chosen)

- Good, because it removes the runtime dependency on BDA entirely - no throttling, no retry latency, on the hot path.
- Good, because it matches an existing, working pattern in the codebase (`config/field_labels/*.json` and `pull-blueprint-fields`).
- Bad, because of the staleness and manual-step tradeoffs above (see Negative Consequences).

## Links

- Implementation: [schemas.py](../../documentai-api/src/documentai_api/utils/schemas.py), [pull_blueprint_schemas.py](../../documentai-api/src/documentai_api/cli/pull_blueprint_schemas.py), `make pull-blueprint-schemas` in [Makefile](../../documentai-api/Makefile)
