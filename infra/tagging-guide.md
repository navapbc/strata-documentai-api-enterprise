# Infrastructure Tagging Guide

The infra drift validator discovers AWS resources using the Resource Groups Tagging API. For it to work, every resource must have these three tags:

| Tag Key | Value |
|---------|-------|
| `project` | `docai` |
| `stage` | `dev` |
| `component` | *(see table below)* |

---

## Resources to Tag

### ECR

| Resource | `component` tag |
|----------|----------------|
| Container image repository | `ecr` |

### S3 Buckets

| Resource | `component` tag |
|----------|----------------|
| Admin UI static site bucket | `admin-ui` |
| Demo UI static site bucket | `demo-ui` |
| Document input bucket | `input-bucket` |
| Document output bucket | `output-bucket` |
| Metrics data bucket | `metrics-bucket` |
| Analytics / Athena results bucket | `analytics` |

### DynamoDB Tables

| Table (by hash key) | `component` tag |
|---------------------|----------------|
| hash_key = `keyHash` | `api-keys` |
| hash_key = `tenantId`, range = `timestamp#eventId` | `audit-events` |
| hash_key = `batchId` | `document-batches` |
| hash_key = `buildId`, range = `pageNumber` | `document-builds` |
| hash_key = `tenantId`, range = `categoryName` | `document-categories` |
| hash_key = `fileName` | `document-metadata` |
| hash_key = `tenantId`, range = `documentType` | `extraction-rules` |
| hash_key = `tenantId` (no range key) | `tenants` |

### Lambda Functions

| Function | `component` tag |
|----------|----------------|
| API handler | `api-gateway` |
| Document processing worker | `document-processor` |
| BDA result handler | `bda-result-processor` |
| Metrics processing | `metrics-processor` |
| Metrics aggregation | `metrics-aggregator` |

### SQS Queues

| Queue | `component` tag |
|-------|----------------|
| Document processor queue | `document-processor` |
| BDA result processor queue | `bda-result-processor` |
| Metrics queue (main + DLQ - 2 queues) | `metrics-queue` |

### API Gateway

| Resource | `component` tag |
|----------|----------------|
| HTTP API | `api-gateway` |

### CloudWatch Logs

| Resource | `component` tag |
|----------|----------------|
| API log group | `api-gateway` |

### Cognito

| Resource | `component` tag |
|----------|----------------|
| User pool | `identity-provider` |

### SSM Parameter Store

| Resource | `component` tag |
|----------|----------------|
| String parameters (4 total) | `config` |
| SecureString parameters | `secrets` |

### Analytics (Glue / Athena)

| Resource | `component` tag |
|----------|----------------|
| Athena workgroup | `analytics` |
| Glue catalog database | `analytics` |

### SNS

| Resource | `component` tag |
|----------|----------------|
| Alerting topic | `monitoring` |

### EventBridge Rules

| Resource | `component` tag |
|----------|----------------|
| S3 trigger rule (doc processing) | `document-processor` |
| BDA completion rule | `bda-result-processor` |
| Scheduled aggregation rules (2) | `metrics-aggregator` |

### IAM Roles

Tag each Lambda execution role with the same `component` value as its Lambda function.

---

## BDA Projects (No Tagging Required)

Bedrock Data Automation projects are discovered via the BDA API directly (not the tagging API). They must exist with names matching these suffixes:

- `all`
- `court_ordered_benefits`
- `debt_obligations`
- `employment_wages`
- `financial_assets`
- `government_benefits`
- `housing_expenses`
- `identity_verification`
- `independent_earnings`
- `private_benefits_and_settlements`
- `receipts_and_invoices`
- `recurring_bills`
- `right_to_work`
- `tax_documents`

**Note:** BDA may only be available in specific regions (e.g. `us-west-2`). If your BDA projects are in a different region, run the validator with `--bda-region us-west-2`.

---

## Running the Validator

After tagging, run from the `infra/` directory:

```bash
uv run python -m validators --env dev --profile YOUR_PROFILE
```

Expected output when tags are applied correctly:

```
67 present  ·  0 missing  ·  0 drifted  ·  0 undiscoverable
```
