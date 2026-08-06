# Audit Log Actor Dropdown: Use Cognito as the Sole Source

- Status: accepted
- Date: 2026-08-06

## Context and Problem Statement

The audit log UI has an actor dropdown that allows admins filter events by an individual who performed the action. Ideally, the dropdown should ideally only show actors relevant to the selected tenant, not every user in the system.

## Decision Drivers

- Actor list should be reasonably scoped to the selected tenant
- Query must be fast regardless of audit event volume
- Solution should not introduce new infrastructure or tables
- Audit events have a 1-year TTL - any derived state must remain consistent with live data

## Considered Options

- **Scan the audit table** - query the tenant's partition and collect distinct `actorEmail` values
- **Sentinel item in the tenant table** - store a `PK: tenantId, SK: "__actors__"` StringSet, updated via `ADD` on every `log_event` write
- **Cognito `list_users()` only** - return all users from the user pool, scoped by tenant where possible

## Decision Outcome

Chosen option: Cognito `list_users()` only - it is fast, requires no derived state, and remains consistent with the live user pool without additional maintenance.

The dropdown is a filter. If a selected actor has no events for the current tenant, the result set is empty. This is an acceptable UX tradeoff given the alternatives.

## Pros and Cons of the Options

### Scan the audit table

- Good, because actors shown are guaranteed to have events for the tenant
- Bad, because read cost scales linearly with audit event volume - a busy tenant with 100k events means 100k items read to populate a dropdown
- Bad, because it is the slowest option at runtime

### Sentinel item in the tenant table (`__actors__` StringSet)

- Good, because actor lookup becomes a single `get_item` - sub-millisecond regardless of audit volume
- Good, because `ADD` on a StringSet is atomic and idempotent under concurrent writes
- Bad, because it mixes concerns: the audit table is append-only immutable facts; a mutable aggregate in the same table is a different access pattern
- Bad, because the sentinel accumulates actors indefinitely - once audit events TTL out, the sentinel still holds those emails, so the dropdown shows actors with no queryable history
- Bad, because fixing TTL staleness requires a periodic rebuild job, adding operational overhead

### Cognito `list_users()` only (chosen)

- Good, because Cognito is already the authoritative user store - no derived state to maintain
- Good, because the list stays consistent with the live user pool automatically
- Good, because it is fast and requires no DynamoDB reads at all for the actor list
- Bad, because it shows all tenant users, not just those who have audit events for the selected tenant; the dropdown may include actors with no relevant history
