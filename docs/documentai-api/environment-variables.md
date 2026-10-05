# Environment Variables

Environment variables are set at deploy time via Terraform. Unlike [feature flags](feature-flags.md), changing these requires a redeploy.

## AWS / BDA

| Variable | Required | Default | Description |
|---|---|---|---|
| `BDA_PROJECT_ARN_ALL` | Yes | - | ARN of the default BDA project used when no per-category project is configured. |
| `BDA_PROFILE_ARN` | Yes | - | ARN of the BDA output profile. |
| `BDA_REGION` | No | `us-east-1` | AWS region where BDA is invoked. |
| `MAX_BDA_INVOKE_RETRY_ATTEMPTS` | No | `3` | Maximum retries on BDA invocation failures. |
| `BEDROCK_CLASSIFICATION_MODEL_ID_PARAM` | Yes | - | SSM parameter name resolving to the Bedrock model ID used for preclassification. |
| `BEDROCK_BOUNDING_BOX_MODEL_ID_PARAM` | No | - | SSM parameter name resolving to the Bedrock model ID used for bounding box extraction. |

## Document AI core

| Variable | Required | Description |
|---|---|---|
| `DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME` | Yes | DynamoDB table for document metadata. |
| `DOCUMENTAI_DOCUMENT_METADATA_JOB_ID_INDEX_NAME` | Yes | GSI name for job ID lookups. |
| `DOCUMENTAI_DOCUMENT_METADATA_BDA_INVOCATION_ID_INDEX_NAME` | Yes | GSI name for BDA invocation ID lookups. |
| `DOCUMENTAI_DOCUMENT_METADATA_TENANT_INDEX_NAME` | Yes | GSI name for tenant-scoped queries. |
| `DOCUMENTAI_DOCUMENT_METADATA_BATCH_ID_INDEX_NAME` | Yes | GSI name for batch ID lookups. |
| `DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME` | Yes | DynamoDB table for document batches. |
| `DOCUMENTAI_BUILD_TABLE_NAME` | Yes | DynamoDB table for build records. |
| `DOCUMENTAI_INPUT_LOCATION` | Yes | S3 URI prefix for document input storage. |
| `DOCUMENTAI_DEMO_INPUT_LOCATION` | No | S3 URI prefix for demo document input. |
| `DOCUMENTAI_OUTPUT_LOCATION` | Yes | S3 URI prefix for processed document output. |
| `DOCUMENTAI_PREPROCESSING_LOCATION` | Yes | S3 URI prefix for preprocessed document storage. |

## Auth / API keys

| Variable | Required | Default | Description |
|---|---|---|---|
| `API_AUTH_ENABLED` | No | `false` | Enables API key authentication. |
| `API_AUTH_CACHE_TTL` | No | `300` | Seconds to cache validated API keys. |
| `API_KEY_PEPPER_PARAM` | No | - | SSM SecureString parameter name for the API key pepper. |
| `API_AUTH_INSECURE_SHARED_KEY_PARAM` | No | - | SSM parameter name for the insecure shared key (non-production use only). |
| `API_AUTH_INSECURE_SHARED_KEY` | No | - | Insecure shared key as a literal env var (non-production use only). |
| `API_KEYS_TABLE_NAME` | Yes | - | DynamoDB table for API keys. |
| `TENANTS_TABLE_NAME` | Yes | - | DynamoDB table for tenant records. |
| `TENANT_REQUEST_COUNTS_TABLE_NAME` | Yes | - | DynamoDB table for per-tenant request counts. |
| `AUDIT_EVENTS_TABLE_NAME` | Yes | - | DynamoDB table for audit events. |

## Extraction rules

| Variable | Required | Description |
|---|---|---|
| `EXTRACTION_RULES_TABLE_NAME` | Yes | DynamoDB table for extraction rules. |
| `DOCUMENT_CATEGORIES_TABLE_NAME` | Yes | DynamoDB table for document categories. |

## Metrics pipeline

| Variable | Required | Description |
|---|---|---|
| `DDB_METRICS_INPUT_QUEUE_URL` | Yes | SQS queue URL for metrics events emitted after each document is processed. |
| `DDB_RAW_DATA_TABLE_NAME` | Yes | DynamoDB table for raw metrics data. |
| `DDB_EXPORT_BUCKET_NAME` | Yes | S3 bucket for raw and aggregated metrics exports. |
| `ATHENA_WORKGROUP_NAME` | Yes | Athena workgroup used for metrics queries. |
| `GLUE_DATABASE_NAME` | Yes | Glue database name for the metrics Athena catalog. |

## App runtime

| Variable | Required | Default | Description |
|---|---|---|---|
| `ENVIRONMENT` | No | `local` | Deployment environment name (e.g. `dev`, `prod`). |
| `IMAGE_TAG` | No | - | Docker image tag, surfaced in health check responses. |
| `HOST` | No | `127.0.0.1` | Host the API server binds to. |
| `PORT` | No | `8000` | Port the API server listens on. |
| `AWS_LAMBDA_FUNCTION_NAME` | - | - | Set automatically by the Lambda runtime. Used internally to detect hosted vs. local execution; do not set manually. |

## OpenTelemetry

See [observability.md](observability.md) for full context on what these enable.

| Variable | Required | Default | Description |
|---|---|---|---|
| `OTEL_SDK_DISABLED` | No | `true` | Set to `false` to enable tracing. Defaults to `true` in code; controlled per environment via the `otel_enabled` Terraform variable. |
| `OTEL_SERVICE_NAME` | No | `documentai-api` | Service name reported in traces and Application Signals metrics. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | `http://localhost:4317` | OTLP gRPC collector endpoint. In Lambda, the `aws-otel-python-instrumentation` layer bypasses this and exports traces directly to the X-Ray daemon via UDP when no explicit traces endpoint is set. |
| `OTEL_AWS_APPLICATION_SIGNALS_ENABLED` | No | `false` | Enables CloudWatch Application Signals metric derivation. Set alongside `OTEL_SDK_DISABLED=false`. |
| `OTEL_METRICS_EXPORTER` | No | - | Set to `awsemf` when Application Signals is enabled to route metrics to CloudWatch EMF. Application Signals metrics appear under the fixed `ApplicationSignals` CloudWatch namespace. |
| `OTEL_EXPORTER_OTLP_LOGS_HEADERS` | No | - | Set to `x-aws-metric-namespace={service-name}` to control the EMF log namespace used internally by the layer. Does not affect the `ApplicationSignals` CloudWatch namespace. |
