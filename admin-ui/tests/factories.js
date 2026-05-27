/**
 * Test factories - build objects with sensible defaults + optional overrides.
 * Usage: buildSession({ email: "custom@co.com" })
 */

export function buildSession(overrides = {}) {
  return {
    accessToken: "test-access-token",
    idToken: "test-id-token",
    refreshToken: "test-refresh-token",
    email: "test@example.com",
    expiresIn: 3600,
    expiresAt: Date.now() + 3600000,
    ...overrides,
  };
}

export function buildTokens(overrides = {}) {
  return {
    accessToken: "test-access-token",
    idToken: "test-id-token",
    refreshToken: "test-refresh-token",
    expiresIn: 3600,
    ...overrides,
  };
}

export function buildTenant(overrides = {}) {
  return {
    tenantId: "test-tenant-id",
    displayName: "Test Tenant",
    primaryContact: "admin@test-tenant.com",
    isActive: true,
    createdAt: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function buildUser(overrides = {}) {
  return {
    email: "user@example.com",
    username: "test-user-name",
    groups: [],
    tenantId: null,
    createdAt: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function buildApiKey(overrides = {}) {
  return {
    tenantId: "test-tenant-id",
    apiKeyName: "test-api-key-name",
    keyPrefix: "tk_abc",
    environment: "dev",
    emailAddress: "dev@example.com",
    isActive: true,
    createdAt: "2026-01-01T00:00:00Z",
    lastUsed: null,
    ...overrides,
  };
}

export function buildDocument(overrides = {}) {
  return {
    jobId: "test-job-id",
    fileName: "test-document.pdf",
    tenantId: "test-tenant",
    processStatus: "completed",
    documentCategory: "general",
    matchedBlueprint: null,
    createdAt: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function buildAuditEvent(overrides = {}) {
  return {
    timestamp: "2026-01-01T00:00:00Z",
    actorEmail: "actor@example.com",
    action: "key.create",
    targetType: "api_key",
    targetId: "tk_abc",
    tenantId: "test-tenant-id",
    metadata: null,
    ...overrides,
  };
}

export function buildCategory(overrides = {}) {
  return {
    tenantId: "test-tenant-id",
    categoryName: "test-category-name",
    displayName: "Test Category",
    description: null,
    isActive: true,
    ...overrides,
  };
}

export function buildField(overrides = {}) {
  return {
    name: "test-field-name",
    type: "string",
    documentType: "W2",
    ...overrides,
  };
}

export function buildMfaChallenge(type = "SOFTWARE_TOKEN_MFA", overrides = {}) {
  return {
    challenge: type,
    session: "test-mfa-session",
    ...overrides,
  };
}

export function buildToken(overrides = {}) {
  return { accessToken: "at", idToken: "it", refreshToken: "rt", expiresIn: 3600, ...overrides };
}

/**
 * Build a fake JWT with custom claims (for e2e/session tests).
 * Returns a 3-part dot-separated string with base64 payload.
 */
export function buildFakeJwt(claims = {}) {
  const payload = btoa(
    JSON.stringify({ email: "test@example.com", "cognito:groups": ["super-admin"], ...claims }),
  );
  return `header.${payload}.signature`;
}
