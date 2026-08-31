# Deprecate Synchronous /wait Endpoints

- Status: accepted
- Date: 2026-08-31

## Context and Problem Statement

Two synchronous "upload and wait" endpoints exist in the API:

- `POST /v1/documents/wait`
- `POST /v1/builds/{build_id}/submit/wait`

Both hold the HTTP connection open, polling DynamoDB until processing completes or a timeout is reached. Both endpoints were originally implemented for an ECS-backed deployment where connection hold time was not constrained.

The API is now deployed behind API Gateway HTTP API (v2), which enforces a hard 30-second integration timeout. BDA extraction commonly takes 30-45 seconds. The gateway kills the connection before processing finishes for any non-trivial document, returning a 5xx to the caller even when the job ultimately succeeds. The endpoints are not reliably usable in the current infrastructure.

`ConfigDefaults.MAX_WAIT_SECONDS = 120` and `ConfigDefaults.ALB_TIMEOUT_BUFFER_SECONDS = 15` are both dead letters - they reference an ALB that no longer exists and a timeout ceiling that is no longer in effect.

## Decision Drivers

- The `/wait` endpoints are broken by design under API Gateway HTTP API - no code change can fix this without changing infrastructure
- No active integrations depend on them; the original ECS-based consumer is on a different codebase
- Keeping both endpoints creates a false impression that synchronous processing is a supported pattern
- The async upload and poll pattern has no timeout ceiling and is the recommended usage pattern

## Considered Options

- **Deprecate `/wait` endpoints, document async as the canonical pattern** (chosen)
- **Deploy an ALB to replace API Gateway** - restores long-lived connections but adds VPC complexity, fixed monthly cost, and more Terraform surface area. No other driver justifies the lift.
- **Lambda response streaming** - Lambda Function URLs and ALB support response streaming, which moves the effective timeout to time-to-first-byte rather than total duration. API Gateway (REST or HTTP API) does not support Lambda response streaming at all, so this would require replacing API Gateway with a Lambda Function URL or ALB as the ingress path - a larger infrastructure change with no other driver.

## Decision Outcome

Chosen option: deprecate `/wait` endpoints. Both endpoints are marked deprecated in their OpenAPI descriptions. `ConfigDefaults.MAX_WAIT_SECONDS` and `ConfigDefaults.ALB_TIMEOUT_BUFFER_SECONDS` are removed. The async upload + poll pattern is documented as the canonical integration path.

The endpoints are not removed immediately to avoid breaking any undiscovered callers, but are candidates for removal in a future cleanup.

### Positive Consequences

- Removes misleading API surface that appears to work but fails silently on slow documents
- Eliminates dead constants that reference non-existent infrastructure
- Makes the canonical integration pattern unambiguous

### Negative Consequences

- Callers that relied on synchronous behavior must switch to async and poll - acceptable given no known active integrations depend on `/wait`
