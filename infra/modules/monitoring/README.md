# Monitoring Module

CloudWatch dashboard, alarms, and SNS notifications for the DocumentAI platform.

## What gets created

- **SNS topic** - always created; alarm target and integration point for subscriptions
- **Email subscriptions** - one per address in `alarm_emails`
- **AWS Chatbot Slack channel** - optional, requires a one-time workspace auth in the console
- **CloudWatch alarms** - gated by `create_alarms` (default off; typically enabled only in prd)
- **CloudWatch dashboard** - gated by `create_dashboard` (all envs by default)

Every alarm sets both `alarm_actions` and `ok_actions` to the SNS topic, so subscribers also receive an auto-resolve notification when an alarm returns to OK.

## Alarm coverage

| Category | Metrics | Condition |
|----------|---------|-----------|
| DLQ depth | `ApproximateNumberOfMessagesVisible` | >= 1 message for 1 period |
| Lambda errors | `Errors` per function | >= `lambda_error_threshold` (default 3) for 1 period |
| Lambda throttles | `Throttles` per function | >= 1 for `lambda_throttle_evaluation_periods` consecutive periods (default 2) |
| Lambda duration | `Duration` max | > 80% of configured timeout for `lambda_duration_evaluation_periods` consecutive periods (default 3) |
| Scheduled worker invocations | `Invocations` sum | < 1 in per-worker `invocation_window_seconds`; missing data treated as breaching. On first apply a newly created alarm starts in ALARM until the first invocation lands - expected for long-window workers (e.g. daily). |
| Metrics queue backlog | `ApproximateAgeOfOldestMessage` | > threshold for 2 periods |
| API Gateway 5xx | `5xx` sum | > threshold for 1 period |
| API Gateway latency | `Latency` p99 | > threshold for 3 periods |

## Dashboard sections

Sections are conditionally rendered based on which inputs are non-null:

1. **Health at a glance** - single-value scorecards (API activity, errors, DLQ, queue)
2. **API** - requests/errors graph with custom log metrics, latency percentiles
3. **Pipeline Health** - Lambda invocations with metric-math error rate %
4. **Pipeline Latency** - p50/p99/max duration per worker
5. **Queues** - analytics queue depth and oldest message age
6. **Dead Letter Queues** - per-DLQ message visibility
7. **Observability Lambdas** - metrics processor/aggregator throughput

## Usage

```hcl
module "monitoring" {
  source = "../../modules/monitoring"

  name_prefix = "docai-prd-123456789012"
  region      = "us-east-1"

  create_dashboard = true
  create_alarms    = true

  # Notifications
  alarm_emails = ["oncall@example.com"]
  slack = {
    workspace_id = "T01234567"
    channel_id   = "C01234567"
  }

  # API Gateway
  api_gateway_id  = module.api_gateway.api_id
  api_log_metrics = module.api_gateway.api_log_metrics

  # Workers
  workers = {
    "Document Processor"   = { function_name = module.workers["document-processor"].function_name, timeout_seconds = 300, pipeline = true, scheduled = false, invocation_window_seconds = null }
    "BDA Result Processor" = { function_name = module.workers["bda-result-processor"].function_name, timeout_seconds = 300, pipeline = true, scheduled = false, invocation_window_seconds = null }
    "Metrics Processor"    = { function_name = module.workers["metrics-processor"].function_name, timeout_seconds = 300, pipeline = false, scheduled = false, invocation_window_seconds = null }
    "Metrics Aggregator"   = { function_name = module.workers["metrics-aggregator"].function_name, timeout_seconds = 300, pipeline = false, scheduled = true, invocation_window_seconds = 600 }
    "Usage Report"         = { function_name = module.workers["usage-report"].function_name, timeout_seconds = 300, pipeline = false, scheduled = true, invocation_window_seconds = 86400 }
  }

  # API Lambda
  api_lambda_function_name   = module.api_gateway.function_name
  api_lambda_timeout_seconds = 30

  # Queues
  metrics_queue_name          = module.metrics_queue.queue_name
  metrics_queue_dlq_name      = module.metrics_queue.dlq_name
  document_processor_dlq_name = module.workers["document-processor"].dlq_name
  bda_output_dlq_name         = module.workers["bda-result-processor"].dlq_name
}
```

## Inputs

All inputs with defaults are optional. Pass `null` to omit a resource category from the dashboard and alarms.

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `name_prefix` | string | - | Prefix for all resource names |
| `region` | string | - | Region for dashboard metrics |
| `create_alarms` | bool | `false` | Enable CloudWatch alarms |
| `create_dashboard` | bool | `true` | Enable CloudWatch dashboard |
| `alarm_emails` | list(string) | `[]` | SNS email subscribers |
| `slack` | object | `null` | Chatbot Slack config (`workspace_id`, `channel_id`) |
| `api_gateway_id` | string | `null` | API Gateway HTTP API id |
| `api_log_metrics` | object | `null` | Custom metrics from access-log filters |
| `workers` | map(object) | `{}` | Worker Lambdas to monitor. Each entry: `function_name`, `timeout_seconds` (duration alarm at 80%), `pipeline` (true = Pipeline sections, false = Observability section), `scheduled` (true = missing-invocations alarm), `invocation_window_seconds` (required when `scheduled = true`; set to the longest expected gap between runs, e.g. 600 for every-5-min, 86400 for daily) |
| `api_lambda_function_name` | string | `null` | API Lambda function name |
| `api_lambda_timeout_seconds` | number | `30` | API Lambda timeout; duration alarm fires at 80% |
| `lambda_error_threshold` | number | `3` | Error count per period before alarm fires |
| `lambda_throttle_evaluation_periods` | number | `2` | Consecutive throttle periods before alarm fires |
| `lambda_duration_evaluation_periods` | number | `3` | Consecutive near-timeout periods before alarm fires |
| `metrics_queue_name` | string | `null` | SQS queue name |
| `metrics_queue_dlq_name` | string | `null` | Metrics queue DLQ name |
| `document_processor_dlq_name` | string | `null` | DLQ name |
| `bda_output_dlq_name` | string | `null` | DLQ name |

Alarm thresholds (`api_5xx_threshold`, `api_p99_latency_threshold_ms`, `queue_max_age_seconds`) have sensible defaults - see `variables.tf`.

## Outputs

| Name | Description |
|------|-------------|
| `sns_topic_arn` | ARN of the alarms SNS topic |

## File structure

```
monitoring/
├── main.tf          # Shared locals, SNS topic, Chatbot/Slack
├── alarms.tf        # All CloudWatch alarm resources
├── dashboard.tf     # Dashboard widget definitions and resource
├── variables.tf     # Input variables
└── outputs.tf       # Module outputs
```
