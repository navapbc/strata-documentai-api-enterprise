// Shared synthetic data for admin console video recording specs.
// Used by admin-walkthrough.spec.js and admin-walkthrough-privacy-mode.spec.js.

export const JOB_ID = "demo-w2-0001";

export const TENANTS = [
  {
    tenantId: "acme-corp",
    displayName: "Acme Corporation",
    maskedTenantId: "labor-workforce",
    primaryContact: "ops@acme.example.com",
    isActive: true,
    createdAt: "2025-01-10T09:00:00Z",
  },
  {
    tenantId: "river-health",
    displayName: "River Health Systems",
    maskedTenantId: "transit-ops",
    primaryContact: "admin@riverhealth.example.com",
    isActive: true,
    createdAt: "2025-03-22T14:30:00Z",
  },
  {
    tenantId: "metro-transit",
    displayName: "Metro Transit Authority",
    maskedTenantId: "public-works",
    primaryContact: "it@metrotransit.example.com",
    isActive: true,
    createdAt: "2025-05-05T11:15:00Z",
  },
];

export const KEYS = [
  {
    tenantId: "acme-corp",
    maskedTenantId: "labor-workforce",
    apiKeyName: "acme-ingest",
    emailAddress: "ops@acme.example.com",
    environment: "prod",
    keyPrefix: "sk_prod_acme",
    createdAt: "2025-02-01T08:00:00Z",
    lastUsed: "2026-07-15T22:10:00Z",
  },
  {
    tenantId: "acme-corp",
    maskedTenantId: "labor-workforce",
    apiKeyName: "acme-staging",
    emailAddress: "dev@acme.example.com",
    environment: "staging",
    keyPrefix: "sk_stg_acme",
    createdAt: "2025-02-01T08:05:00Z",
    lastUsed: "2026-07-14T10:00:00Z",
  },
  {
    tenantId: "river-health",
    maskedTenantId: "transit-ops",
    apiKeyName: "rh-prod",
    emailAddress: "admin@riverhealth.example.com",
    environment: "prod",
    keyPrefix: "sk_prod_rh",
    createdAt: "2025-04-01T12:00:00Z",
    lastUsed: "2026-07-16T08:45:00Z",
  },
  {
    tenantId: "metro-transit",
    maskedTenantId: "public-works",
    apiKeyName: "mt-ingest",
    emailAddress: "it@metrotransit.example.com",
    environment: "prod",
    keyPrefix: "sk_prod_mt",
    createdAt: "2025-06-01T09:30:00Z",
    lastUsed: null,
  },
];

export const USERS = [
  {
    username: "user-001",
    email: "admin@acme.example.com",
    status: "approved",
    role: "tenant-admin",
    tenantId: "acme-corp",
    createdAt: "2025-02-01T07:00:00Z",
  },
  {
    username: "user-002",
    email: "ops@riverhealth.example.com",
    status: "approved",
    role: "tenant-admin",
    tenantId: "river-health",
    createdAt: "2025-03-22T14:00:00Z",
  },
  {
    username: "user-003",
    email: "newuser@metrotransit.example.com",
    status: "pending",
    role: null,
    tenantId: null,
    createdAt: "2026-07-16T09:00:00Z",
  },
];

export const DOCUMENTS = [
  {
    jobId: JOB_ID,
    fileName: "employee-w2-2025.png",
    processStatus: "success",
    matchedBlueprint: "US Tax Form W-2",
    tenantId: "acme-corp",
    createdAt: "2026-07-16T15:55:00Z",
  },
  {
    jobId: "job-002",
    fileName: "invoice-4471.pdf",
    processStatus: "success",
    matchedBlueprint: "Invoice",
    tenantId: "acme-corp",
    createdAt: "2026-07-16T15:10:00Z",
  },
  {
    jobId: "job-003",
    fileName: "drivers-license.jpg",
    processStatus: "success",
    matchedBlueprint: "US Driver License",
    tenantId: "river-health",
    createdAt: "2026-07-16T14:30:00Z",
  },
  {
    jobId: "job-004",
    fileName: "blurry-scan.png",
    processStatus: "blurry_document_detected",
    matchedBlueprint: null,
    tenantId: "acme-corp",
    createdAt: "2026-07-15T22:05:00Z",
  },
  {
    jobId: "job-005",
    fileName: "receipt-scan.png",
    processStatus: "no_custom_blueprint_matched",
    matchedBlueprint: null,
    tenantId: "metro-transit",
    createdAt: "2026-07-15T18:30:00Z",
  },
];

export const AUDIT_EVENTS = [
  {
    eventId: "evt-001",
    timestamp: "2026-07-16T15:00:00Z",
    actorEmail: "admin@example.com",
    action: "tenant.create",
    targetType: "tenant",
    targetId: "metro-transit",
    tenantId: null,
    metadata: {},
  },
  {
    eventId: "evt-002",
    timestamp: "2026-07-16T14:30:00Z",
    actorEmail: "admin@example.com",
    action: "api-key.create",
    targetType: "api-key",
    targetId: "mt-ingest",
    tenantId: "metro-transit",
    metadata: {},
  },
  {
    eventId: "evt-003",
    timestamp: "2026-07-16T09:10:00Z",
    actorEmail: "admin@example.com",
    action: "user.approve",
    targetType: "user",
    targetId: "user-003",
    tenantId: null,
    metadata: {},
  },
  {
    eventId: "evt-004",
    timestamp: "2026-07-15T22:00:00Z",
    actorEmail: "admin@example.com",
    action: "extraction-rules.update",
    targetType: "extraction-rules",
    targetId: "acme-corp",
    tenantId: "acme-corp",
    metadata: { documentType: "US Tax Form W-2" },
  },
  {
    eventId: "evt-005",
    timestamp: "2026-07-15T18:00:00Z",
    actorEmail: "admin@example.com",
    action: "doc-category.create",
    targetType: "doc-category",
    targetId: "pay-stub",
    tenantId: "acme-corp",
    metadata: {},
  },
];

export const DOC_CATEGORIES = [
  {
    tenantId: "acme-corp",
    categoryName: "pay-stub",
    displayName: "Pay Stub",
    description: "Employee pay stubs",
    processingPercentage: 1,
    isAutoRegistered: false,
    isActive: true,
    createdAt: "2026-07-15T18:00:00Z",
  },
  {
    tenantId: "acme-corp",
    categoryName: "w2-form",
    displayName: "W-2 Form",
    description: "Annual tax forms",
    processingPercentage: 1,
    isAutoRegistered: true,
    isActive: true,
    createdAt: "2026-01-10T09:00:00Z",
  },
  {
    tenantId: "river-health",
    categoryName: "drivers-license",
    displayName: "Driver License",
    description: "State-issued ID",
    processingPercentage: 0.5,
    isAutoRegistered: false,
    isActive: true,
    createdAt: "2026-03-22T14:00:00Z",
  },
];

export const EXTRACTION_FIELDS = [
  { name: "employerName", documentType: "US Tax Form W-2", type: "string" },
  { name: "employeeName", documentType: "US Tax Form W-2", type: "string" },
  { name: "wages", documentType: "US Tax Form W-2", type: "currency" },
  {
    name: "federalIncomeTaxWithheld",
    documentType: "US Tax Form W-2",
    type: "currency",
  },
  { name: "taxYear", documentType: "US Tax Form W-2", type: "integer" },
  { name: "invoiceNumber", documentType: "Invoice", type: "string" },
  { name: "invoiceDate", documentType: "Invoice", type: "date" },
  { name: "totalAmount", documentType: "Invoice", type: "currency" },
];

export const METRICS_RESP = {
  summary: {
    totalRecords: 1840,
    totalExtractionInvocations: 1720,
    totalDocumentsRecognized: 1650,
    byResponseCode: { "000": 1580, 101: 70, 410: 60, 900: 130 },
    byClassification: {
      "US Tax Form W-2": 820,
      Invoice: 540,
      "US Driver License": 290,
      null: 190,
    },
    byFileType: { "image/png": 910, "image/jpeg": 540, "application/pdf": 390 },
    byUserCategory: {
      "pay-stub": 480,
      "w2-form": 820,
      "drivers-license": 290,
      null: 250,
    },
    byUploadMethod: { api: 1640, console: 200 },
    timingStats: {
      bdaProcessingTimeAvg: 27.1,
      bdaWaitTimeAvg: 2.3,
      totalProcessingTimeAvg: 29.4,
    },
  },
  dailyStats: [
    {
      date: "2026-07-10",
      totalRecords: 240,
      bdaInvocations: 225,
      successCount: 210,
      bdaProcessingTimeAvg: 26.8,
      totalProcessingTimeAvg: 29.1,
    },
    {
      date: "2026-07-11",
      totalRecords: 195,
      bdaInvocations: 182,
      successCount: 174,
      bdaProcessingTimeAvg: 27.3,
      totalProcessingTimeAvg: 29.6,
    },
    {
      date: "2026-07-12",
      totalRecords: 310,
      bdaInvocations: 291,
      successCount: 278,
      bdaProcessingTimeAvg: 27.0,
      totalProcessingTimeAvg: 29.3,
    },
    {
      date: "2026-07-13",
      totalRecords: 280,
      bdaInvocations: 263,
      successCount: 251,
      bdaProcessingTimeAvg: 27.4,
      totalProcessingTimeAvg: 29.7,
    },
    {
      date: "2026-07-14",
      totalRecords: 320,
      bdaInvocations: 300,
      successCount: 287,
      bdaProcessingTimeAvg: 26.9,
      totalProcessingTimeAvg: 29.2,
    },
    {
      date: "2026-07-15",
      totalRecords: 265,
      bdaInvocations: 248,
      successCount: 237,
      bdaProcessingTimeAvg: 27.2,
      totalProcessingTimeAvg: 29.5,
    },
    {
      date: "2026-07-16",
      totalRecords: 230,
      bdaInvocations: 211,
      successCount: 143,
      bdaProcessingTimeAvg: 27.5,
      totalProcessingTimeAvg: 29.8,
    },
  ],
};

export const USAGE_RESP = {
  month: "2026-07",
  tenants: [
    {
      tenantId: "acme-corp",
      maskedTenantId: "labor-workforce",
      totalRecords: 980,
      totalBdaPages: 1240,
      totalFileSizeBytes: 312_000_000,
    },
    {
      tenantId: "river-health",
      maskedTenantId: "transit-ops",
      totalRecords: 540,
      totalBdaPages: 680,
      totalFileSizeBytes: 178_000_000,
    },
    {
      tenantId: "metro-transit",
      maskedTenantId: "public-works",
      totalRecords: 320,
      totalBdaPages: 410,
      totalFileSizeBytes: 104_000_000,
    },
  ],
};

export const SCHEMAS = [
  {
    documentType: "W2",
    description:
      "A tax form to file personal income received from an employer in a fiscal year",
    category: "employer_income",
    fieldCount: 12,
  },
  {
    documentType: "Payslip",
    description:
      "A document issued by an employer containing wages received for a given period.",
    category: "employer_income",
    fieldCount: 8,
  },
  {
    documentType: "Bank-Statement",
    description:
      "A financial statement listing transaction summaries for a specific duration",
    category: "account_statements",
    fieldCount: 10,
  },
  {
    documentType: "US-drivers-licenses",
    description: "US driving license from any US state",
    category: "identity",
    fieldCount: 14,
  },
  {
    documentType: "US-passports",
    description: "A passport from the United States of America",
    category: "identity",
    fieldCount: 9,
  },
];
