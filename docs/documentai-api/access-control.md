# Multi-tenancy and access control

The platform is designed to serve multiple organizations from a single deployment. Each organization is a **tenant** - fully isolated from every other tenant. Users and API keys belong to a tenant, and data is always scoped to the tenant it came from.

## Tenants

A tenant represents an organization or team using the platform. Each tenant has its own:

- Users (managed through the admin console)
- API keys (for programmatic access)
- Documents and processing results
- Extraction rules

A tenant-admin can only see and manage their own tenant's data. There is no way for one tenant to access another tenant's documents, users, or configuration.

## Roles

There are two roles in the system:

**Tenant-admin** - manages a single tenant. Can create and manage users within their tenant, generate and revoke API keys, configure extraction rules, and review processed documents. Cannot see or affect any other tenant.

**Super-admin** - manages the platform across all tenants. Can create tenants, assign users to tenants, and perform any action a tenant-admin can perform. Intended for platform operators, not end users.

New accounts that sign up have a valid login but no role. They can authenticate but cannot access any admin functionality until a super-admin assigns them a role and tenant. This is intentional - it prevents unauthorized access from self-registered accounts.

## API keys

API keys are how programmatic clients (integrations, batch jobs, other services) authenticate with the platform. Each key is:

- Scoped to a single tenant - a key can only submit and retrieve documents for its own tenant
- Named - so you can identify which system is using which key
- Revocable - deactivating a key takes effect immediately
- Optionally expiring - you can set an expiration date when creating a key

The plaintext key is shown once at creation and never stored. Only a hash is kept in the database. If a key is lost, it must be revoked and a new one generated.

## How authentication works

The platform supports two authentication methods:

**JWT (admin console users)** - users sign in through Cognito with email/password and TOTP MFA (or Google SSO if configured). The resulting token carries the user's role and tenant assignment. Admin console sessions use this method.

**API key (programmatic clients)** - passed as a header on each request. The platform looks up the key hash, checks it's active and not expired, and resolves the tenant from the key record. No session, no token refresh.

Some endpoints accept both - for example, the document submission endpoint can be called by an API key client or by an admin console user reviewing documents for their tenant.

## What tenant isolation means in practice

When a request comes in, the platform resolves the tenant from the credential - either the tenant assigned to the API key, or the `custom:tenant_id` claim in the JWT. Every database query, every S3 path, every result is filtered to that tenant.

A tenant-admin who tries to request data for a different tenant gets a 403. An API key that tries to submit documents under a different tenant ID gets a 403. There is no way to escalate access within the system - only a super-admin can operate across tenant boundaries.
