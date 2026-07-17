# Authorization

The platform supports two ways to authenticate: interactive sign-in for users accessing the admin console, and API keys for programmatic clients submitting documents.

## User sign-in (admin console)

Admin console users sign in with email and password through AWS Cognito, followed by a one-time code from an authenticator app (TOTP MFA). Successful sign-in produces a short-lived token that the browser includes with every request. The token carries the user's role and tenant assignment - the API uses these to determine what the user is allowed to see and do.

Google SSO is optionally available. When enabled, users can sign in with a Google account instead of email and password. The platform receives the same Cognito token either way - the API backend requires no changes to support it.

## API keys (programmatic clients)

Integrations, batch jobs, and other services authenticate using an API key passed as a header on each request. Keys are scoped to a single tenant - a key can only submit and retrieve documents for the tenant it was created under.

Keys are named so you can identify which system is using which key. They can be revoked immediately from the admin console, and optionally set to expire on a specific date. The plaintext key is shown once at creation and never stored - only a hash is kept. If a key is lost, it must be revoked and a new one generated.

## What happens without a valid credential

Requests without a valid token or API key are rejected with a 401. Users who have signed up but haven't been assigned a role by a super-admin can authenticate but cannot access any functionality - they see a pending approval screen until their account is configured.

For more on roles and tenant assignment, see [Multi-tenancy and access control](access-control.md).
