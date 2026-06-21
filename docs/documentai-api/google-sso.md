# Google SSO (Federated Sign-In)

The admin and demo UIs support optional "Sign in with Google" via Cognito's federated identity provider integration. When enabled, users authenticate with Google and receive standard Cognito JWTs - the API backend requires no changes.

## How It Works

1. The UI redirects to Cognito's hosted OAuth2 `/authorize` endpoint with `identity_provider=Google`
2. Cognito handles the Google OAuth flow and issues its own JWT tokens
3. The API validates these tokens using the same Cognito JWKS endpoint used for email/password sign-ins
4. PKCE (S256) and CSRF state are used to protect the authorization code flow

## Enabling Google SSO

### 1. Create a Google OAuth 2.0 client

In the [Google Cloud Console](https://console.cloud.google.com/apis/credentials):

- Application type: **Web application**
- Authorized redirect URI: `https://<cognito-domain>.auth.<region>.amazoncognito.com/oauth2/idpresponse`

The Cognito domain will be `<service-name>-console-auth` (e.g. `docai-dev-123456789012-console-auth`).

### 2. Store credentials in SSM

Never commit these values to the repository. Store them as SSM parameters:

```bash
aws ssm put-parameter \
  --name "/<project>/<env>/google-oauth-client-id" \
  --type String \
  --value "<your-google-client-id>.apps.googleusercontent.com"

aws ssm put-parameter \
  --name "/<project>/<env>/google-oauth-client-secret" \
  --type SecureString \
  --value "<your-google-client-secret>"
```

For example, with the default project name and dev environment:

```bash
aws ssm put-parameter \
  --name "/docai/dev/google-oauth-client-id" \
  --type String \
  --value "123456789-abc.apps.googleusercontent.com"

aws ssm put-parameter \
  --name "/docai/dev/google-oauth-client-secret" \
  --type SecureString \
  --value "GOCSPX-..."
```

### 3. Enable in Terraform

Set the variable in your `terraform.tfvars` or pass it via CLI/CI:

```hcl
google_sso_enabled = true
```

### 4. Apply infrastructure

```bash
make infra-apply ENVIRONMENT=dev
```

This creates:
- A Cognito user pool domain (required for OAuth flows)
- A Google identity provider linked to the user pool
- Updates the app client to accept Google as an identity provider

### 5. Update UI config

Both `ui/admin/config.json` and `ui/demo/config.json` (`.gitignore`d) need:

```json
{
  "cognito_domain": { "value": "<cognito-domain-prefix>" },
  "cognito_google_enabled": { "value": true }
}
```

The domain value is output by Terraform:

```bash
cd infra/environments/dev
terraform output cognito_domain
```

## Disabling Google SSO

Set `google_sso_enabled = false` (the default) and re-apply. The Google button will be hidden in the UI automatically when `cognito_google_enabled` is `false` or absent in `config.json`.

## Email Domain Restriction

There are two ways to restrict which Google accounts can sign in:

### Option A: Google Workspace (simplest)

If you have a Google Workspace, set the OAuth consent screen to **Internal** in the [Google Cloud Console](https://console.cloud.google.com/apis/credentials/consent). Only users in your Workspace org (e.g. `@yourcompany.com`) can authenticate - Google enforces this before Cognito ever sees the user. No Lambda needed.

### Option B: Pre-signup Lambda (for External apps)

If you don't have Google Workspace, or need to allow multiple specific domains, set:

```hcl
google_allowed_domains = ["yourcompany.com", "partner.org"]
```

This deploys a Cognito pre-sign-up Lambda trigger that rejects users whose email domain isn't in the list. Users see an error like "Email domain 'gmail.com' is not allowed."

With an empty list (the default), all Google accounts are accepted.

**For the demo UI**: There's no `isApproved()` gate like the admin UI has, so any allowed Google account gets immediate access. Decide whether that's intentional (public demo) or whether you need domain restrictions.

**For the admin UI**: Even without domain restrictions, Google SSO users still need a super-admin to place them in a Cognito group before they can do anything beyond the "pending approval" screen.

## MFA Considerations

Google SSO users bypass the TOTP MFA flow. Cognito does not trigger MFA challenges for federated sign-ins - Google's own security (2FA on the Google account) is relied upon instead.

If your security policy requires MFA for all admin access, options:

1. **Accept Google's MFA** - Google accounts with 2-step verification enabled provide equivalent protection. This is the most common approach.
2. **Don't enable Google SSO for admin** - Only enable it for the demo UI (`cognito_google_enabled: true` in demo config only, `false` in admin config). The admin UI button stays hidden.
3. **Post-auth MFA** - Implement application-level TOTP verification after Google sign-in (significant extra work, rarely justified).

## Security

- Google OAuth credentials are stored in AWS SSM Parameter Store (`SecureString`), never in the repository
- The `google_client_secret` Terraform variable is marked `sensitive`
- `config.json` is `.gitignore`d - no secrets are needed client-side (only the Cognito domain prefix, which is public)
- `gitleaks` default ruleset catches Google OAuth secrets if accidentally committed
- Google SSO defaults to **disabled** - opt-in only

## Architecture

```
Browser                    Cognito                         Google
  │                          │                              │
  ├── /authorize ──────────► │                              │
  │   (identity_provider=    │── OAuth redirect ──────────► │
  │    Google, PKCE, state)  │                              │
  │                          │◄─── auth code ──────────────┤
  │◄── redirect /callback ──┤                              │
  │    (code + state)        │                              │
  │                          │                              │
  ├── POST /oauth2/token ──► │                              │
  │   (code + code_verifier) │                              │
  │◄── Cognito JWT ─────────┤                              │
  │                          │                              │
  ├── API call ────────────────────────────────────────────►│ (API Gateway)
  │   (Authorization: Bearer <cognito-jwt>)                 │
```

The API never talks to Google directly. It validates the Cognito-issued JWT the same way it does for email/password sign-ins.
