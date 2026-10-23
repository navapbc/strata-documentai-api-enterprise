# Presentation Mode



Presentation mode is a screen-sharing safety feature for the admin console. When active, tenant IDs, user emails, and other identifying values are replaced with deterministic fake names so that real customer data is never visible during demos or recorded walkthroughs.

## See it in action

![Presentation mode toggle - real tenant IDs replaced with masked names](media/admin-walkthrough-presentation-mode.gif)

## Activating presentation mode

Click the **Presentation Mode** toggle in the main login screen. The state is stored in `sessionStorage` under the key `presentation_mode` and is cleared automatically when the browser tab is closed.

## What gets masked

| Surface | Real value | Presentation mode value |
|---|---|---|
| Sidebar user email | `user@example.com` | `"Presentation Mode"` |
| Document watermark | real session email | `user@example.com` |
| Tenant IDs (usage table, audit log, tenant list, API keys) | `acme-corp` | deterministic fake e.g. `labor-workforce` |
| User emails (users table, audit actor list) | `jane@acme.com` | deterministic fake e.g. `j.smith@demo-agency.gov` |
| Audit actor filter | enabled | disabled (see below) |

Masked values are **deterministic** - the same real value always maps to the same fake value within a session, so relationships between rows remain consistent.

## How it works

### Frontend

`isPresentationMode()` in `ui/shared/utils/presentation-mode.js` reads `sessionStorage` and is the client-side source of truth. Views call it at render time to decide whether to display real or masked values.

### API

The API always returns real IDs. For fields that need masking, a parallel `masked_*` field is populated when the request carries the `X-Presentation-Mode: true` header (injected by the HTTP service when `isPresentationMode()` is true):

- `masked_tenant_id` on `TenantUsage`, `AuditEventItem`, `TenantItem`, `ApiKeyItem`, `UserItem`, `DocumentCategoryItem`
- masked `actor_email` / `username` / `email` on `AuditEventItem` and `UserItem`

The UI swaps in the `masked_*` value for display while keeping the real value for filter and API calls.

### Masking algorithm

`presentation_mask.py` uses a sha256-based hash to map each real value to a fixed index into a list of demo names (`DEMO_TENANTS`, `DEMO_FIRST_NAMES`, etc. in `config/presentation_mask.py`). The hash is deterministic across requests but not reversible.

## Limitations

- **Not a security control.** Real IDs are still present in API responses and visible in browser developer tools. Presentation mode only prevents accidental on-screen exposure.
- **Audit actor filter is disabled** in presentation mode because the filter works by matching `actor_email`, which is masked. A future fix would add a DynamoDB GSI on `actor_sub` and filter by that instead (see TODO in `audit-log.js`).
- **`__global__` tenant** is never masked. It represents system-level events not scoped to any tenant and renders as `"-"` in the UI.
