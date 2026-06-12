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
| DLQ depth | `ApproximateNumberOfMessagesVisible` | ≥ 1 message for 1 period |
| Lambda errors | `Errors` per function | ≥ 1 for 1 period |
| Lambda throttles | `Throttles` per function | ≥ 1 for 1 period |
| Lambda duration | `Duration` max | > 80% of configured timeout for 1 period |
| ALB 5xx | `HTTPCode_Target_5XX_Count` | > threshold for 1 period |
| ALB unhealthy hosts | `UnHealthyHostCount` | ≥ 1 for 2 periods |
| ALB latency | `TargetResponseTime` p99 | > threshold for 3 periods |
| ECS CPU | `CPUUtilization` avg | > threshold for 3 periods |
| ECS memory | `MemoryUtilization` avg | > threshold for 3 periods |
| Metrics queue backlog | `ApproximateAgeOfOldestMessage` | > threshold for 2 periods |
| API Gateway 5xx | `5xx` sum | > threshold for 1 period |
| API Gateway latency | `Latency` p99 | > threshold for 3 periods |

## Dashboard sections

Sections are conditionally rendered based on which inputs are non-null:

1. **Health at a glance** - single-value scorecards (API activity, errors, DLQ, queue)
2. **API** - requests/errors graph with custom log metrics, latency percentiles
3. **ECS / API** - running tasks, CPU, memory, ALB errors
4. **Pipeline Health** - Lambda invocations with metric-math error rate %
5. **Pipeline Latency** - p50/p99/max duration per worker
6. **Queues** - analytics queue depth and oldest message age
7. **Dead Letter Queues** - per-DLQ message visibility
8. **Observability Lambdas** - metrics processor/aggregator throughput

## Usage

The API surface has two mutually exclusive paths: provide *either* the API Gateway inputs (`api_gateway_id`, `api_log_metrics`) *or* the ECS/ALB inputs (`alb_arn_suffix`, `target_group_arn_suffix`, `ecs_cluster_name`, `ecs_service_name`). Pass `null` for the path you aren't using.

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

  # API Gateway path
  api_gateway_id  = module.api_gateway[0].api_id
  api_log_metrics = module.api_gateway[0].api_log_metrics

  # ECS/ALB path (pass null when using API Gateway)
  alb_arn_suffix          = null
  target_group_arn_suffix = null
  ecs_cluster_name        = null
  ecs_service_name        = null

  # Workers
  document_processor_function_name   = module.document_processor.function_name
  bda_result_processor_function_name = module.bda_result_processor.function_name
  metrics_processor_function_name    = module.metrics_processor.function_name
  metrics_aggregator_function_name   = module.metrics_aggregator.function_name

  # Queues
  metrics_queue_name          = module.metrics_queue.queue_name
  document_processor_dlq_name = module.document_processor.dlq_name
  bda_output_dlq_name         = module.bda_result_processor.dlq_name
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
| `alb_arn_suffix` | string | `null` | ALB ARN suffix for metrics |
| `target_group_arn_suffix` | string | `null` | Target group ARN suffix |
| `ecs_cluster_name` | string | `null` | ECS cluster name |
| `ecs_service_name` | string | `null` | ECS service name |
| `document_processor_function_name` | string | `null` | Lambda function name |
| `bda_result_processor_function_name` | string | `null` | Lambda function name |
| `metrics_processor_function_name` | string | `null` | Lambda function name |
| `metrics_aggregator_function_name` | string | `null` | Lambda function name |
| `worker_timeout_seconds` | number | `300` | Duration alarm threshold base |
| `metrics_queue_name` | string | `null` | SQS queue name |
| `document_processor_dlq_name` | string | `null` | DLQ name |
| `bda_output_dlq_name` | string | `null` | DLQ name |

Alarm thresholds (`alb_5xx_threshold`, `ecs_cpu_threshold`, etc.) have sensible defaults - see `variables.tf`.

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
