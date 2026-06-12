# Monitoring module: SNS topic + alarms + a CloudWatch dashboard.
#
# Dashboard layout is ported from the CDK reference
# (idp-platform-copa-v2/lib/stacks/cloudwatch-dashboard-stack.ts), sourcing
# identifiers from module outputs instead of SSM lookups.
#
# Alarms are gated by var.create_alarms (prd only); the dashboard by
# var.create_dashboard (all envs). The SNS topic is always created so whoever
# has prod access can attach subscriptions later via tfvars without a code change.

variable "name_prefix" {
  type        = string
  description = "Prefix for dashboard/topic/alarm names, e.g. docai-prd-<account>"
}

variable "region" {
  type        = string
  description = "Region for dashboard widget metrics"
}

variable "create_alarms" {
  type    = bool
  default = false
}

variable "create_dashboard" {
  type    = bool
  default = true
}

# --- Notification endpoints ---

variable "alarm_emails" {
  type        = list(string)
  description = "Email addresses to subscribe to the alarm SNS topic"
  default     = []
}

variable "slack" {
  type = object({
    workspace_id = string # Slack team/workspace id (from the one-time Chatbot auth)
    channel_id   = string
  })
  description = "Optional AWS Chatbot Slack target. Requires a one-time workspace authorization in the console."
  default     = null
}

# --- API target (ECS + ALB path) ---

variable "alb_arn_suffix" {
  type    = string
  default = null
}

variable "target_group_arn_suffix" {
  type    = string
  default = null
}

variable "ecs_cluster_name" {
  type    = string
  default = null
}

variable "ecs_service_name" {
  type    = string
  default = null
}

# --- API target (API Gateway HTTP API path) ---

variable "api_gateway_id" {
  type        = string
  description = "API Gateway HTTP API id (ApiId dimension) for request/error/latency metrics"
  default     = null
}

variable "api_log_metrics" {
  type = object({
    namespace        = string
    submitted_metric = string
    polls_metric     = string
  })
  description = <<-EOT
    Custom CloudWatch metrics (from the API access-log metric filters) that split
    document submissions from status-poll GETs. When set, the API scorecard and the
    request graph lead with these instead of the poll-inflated API Gateway Count.
  EOT
  default     = null
}

# --- Workers (Lambda) ---

variable "document_processor_function_name" {
  type    = string
  default = null
}

variable "bda_result_processor_function_name" {
  type    = string
  default = null
}

variable "metrics_processor_function_name" {
  type    = string
  default = null
}

variable "metrics_aggregator_function_name" {
  type    = string
  default = null
}

variable "worker_timeout_seconds" {
  type        = number
  description = "Configured timeout for worker Lambdas; duration alarm fires at 80% of this"
  default     = 300
}

# --- Queues ---

variable "metrics_queue_name" {
  type    = string
  default = null
}

variable "document_processor_dlq_name" {
  type    = string
  default = null
}

variable "bda_output_dlq_name" {
  type    = string
  default = null
}

# --- Alarm thresholds ---

variable "alb_5xx_threshold" {
  type    = number
  default = 5
}

variable "alb_p99_latency_threshold_seconds" {
  type    = number
  default = 2
}

variable "ecs_cpu_threshold" {
  type    = number
  default = 80
}

variable "ecs_memory_threshold" {
  type    = number
  default = 80
}

variable "queue_max_age_seconds" {
  type    = number
  default = 900
}

variable "api_5xx_threshold" {
  type    = number
  default = 5
}

variable "api_p99_latency_threshold_ms" {
  type    = number
  default = 3000
}

locals {
  period = 300

  # Worker function names that exist (drop nulls), used for error/throttle/duration alarms.
  worker_function_names = compact([
    var.document_processor_function_name,
    var.bda_result_processor_function_name,
    var.metrics_processor_function_name,
    var.metrics_aggregator_function_name,
  ])

  dlq_names = compact([
    var.document_processor_dlq_name,
    var.bda_output_dlq_name,
  ])

  duration_alarm_threshold_ms = var.worker_timeout_seconds * 1000 * 0.8

  # Gate sets for for_each alarms.
  alarm_worker_names = var.create_alarms ? toset(local.worker_function_names) : toset([])
  alarm_dlq_names    = var.create_alarms ? toset(local.dlq_names) : toset([])
  has_alb            = var.alb_arn_suffix != null && var.target_group_arn_suffix != null
  has_ecs            = var.ecs_cluster_name != null && var.ecs_service_name != null
}

# --- SNS topic + subscriptions ---

resource "aws_sns_topic" "alarms" {
  name = "${var.name_prefix}-alarms"
}

resource "aws_sns_topic_subscription" "email" {
  for_each  = toset(var.alarm_emails)
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = each.value
}

# --- Optional AWS Chatbot → Slack ---

data "aws_iam_policy_document" "chatbot_assume" {
  count = var.slack != null ? 1 : 0
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["chatbot.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "chatbot" {
  count              = var.slack != null ? 1 : 0
  name               = "${var.name_prefix}-chatbot"
  assume_role_policy = data.aws_iam_policy_document.chatbot_assume[0].json
}

resource "aws_iam_role_policy_attachment" "chatbot_readonly" {
  count      = var.slack != null ? 1 : 0
  role       = aws_iam_role.chatbot[0].name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchReadOnlyAccess"
}

resource "aws_chatbot_slack_channel_configuration" "this" {
  count              = var.slack != null ? 1 : 0
  configuration_name = "${var.name_prefix}-slack"
  iam_role_arn       = aws_iam_role.chatbot[0].arn
  slack_channel_id   = var.slack.channel_id
  slack_team_id      = var.slack.workspace_id
  sns_topic_arns     = [aws_sns_topic.alarms.arn]
}

# --- Alarms: DLQ depth (keystone) ---

resource "aws_cloudwatch_metric_alarm" "dlq_depth" {
  for_each = local.alarm_dlq_names

  alarm_name          = "${each.value}-not-empty"
  alarm_description   = "Messages present in DLQ ${each.value} - failed processing."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  dimensions          = { QueueName = each.value }
  statistic           = "Maximum"
  period              = local.period
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}

# --- Alarms: Lambda errors / throttles / duration ---

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = local.alarm_worker_names

  alarm_name          = "${each.value}-errors"
  alarm_description   = "Lambda ${each.value} reported errors."
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = each.value }
  statistic           = "Sum"
  period              = local.period
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  for_each = local.alarm_worker_names

  alarm_name          = "${each.value}-throttles"
  alarm_description   = "Lambda ${each.value} is being throttled."
  namespace           = "AWS/Lambda"
  metric_name         = "Throttles"
  dimensions          = { FunctionName = each.value }
  statistic           = "Sum"
  period              = local.period
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  for_each = local.alarm_worker_names

  alarm_name          = "${each.value}-duration-near-timeout"
  alarm_description   = "Lambda ${each.value} max duration exceeded 80% of its timeout."
  namespace           = "AWS/Lambda"
  metric_name         = "Duration"
  dimensions          = { FunctionName = each.value }
  statistic           = "Maximum"
  period              = local.period
  evaluation_periods  = 1
  threshold           = local.duration_alarm_threshold_ms
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}

# --- Alarms: ALB ---

resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  count = var.create_alarms && local.has_alb ? 1 : 0

  alarm_name          = "${var.name_prefix}-alb-target-5xx"
  alarm_description   = "ALB target 5xx responses exceeded threshold."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_Target_5XX_Count"
  dimensions          = { LoadBalancer = var.alb_arn_suffix, TargetGroup = var.target_group_arn_suffix }
  statistic           = "Sum"
  period              = local.period
  evaluation_periods  = 1
  threshold           = var.alb_5xx_threshold
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "alb_unhealthy_hosts" {
  count = var.create_alarms && local.has_alb ? 1 : 0

  alarm_name          = "${var.name_prefix}-alb-unhealthy-hosts"
  alarm_description   = "ALB target group has unhealthy hosts."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "UnHealthyHostCount"
  dimensions          = { LoadBalancer = var.alb_arn_suffix, TargetGroup = var.target_group_arn_suffix }
  statistic           = "Maximum"
  period              = local.period
  evaluation_periods  = 2
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "alb_latency" {
  count = var.create_alarms && local.has_alb ? 1 : 0

  alarm_name          = "${var.name_prefix}-alb-p99-latency"
  alarm_description   = "ALB p99 target response time is high."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "TargetResponseTime"
  dimensions          = { LoadBalancer = var.alb_arn_suffix, TargetGroup = var.target_group_arn_suffix }
  extended_statistic  = "p99"
  period              = local.period
  evaluation_periods  = 3
  threshold           = var.alb_p99_latency_threshold_seconds
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}

# --- Alarms: ECS ---

resource "aws_cloudwatch_metric_alarm" "ecs_cpu" {
  count = var.create_alarms && local.has_ecs ? 1 : 0

  alarm_name          = "${var.name_prefix}-ecs-cpu-high"
  alarm_description   = "ECS service CPU utilization is high."
  namespace           = "AWS/ECS"
  metric_name         = "CPUUtilization"
  dimensions          = { ClusterName = var.ecs_cluster_name, ServiceName = var.ecs_service_name }
  statistic           = "Average"
  period              = local.period
  evaluation_periods  = 3
  threshold           = var.ecs_cpu_threshold
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "ecs_memory" {
  count = var.create_alarms && local.has_ecs ? 1 : 0

  alarm_name          = "${var.name_prefix}-ecs-memory-high"
  alarm_description   = "ECS service memory utilization is high."
  namespace           = "AWS/ECS"
  metric_name         = "MemoryUtilization"
  dimensions          = { ClusterName = var.ecs_cluster_name, ServiceName = var.ecs_service_name }
  statistic           = "Average"
  period              = local.period
  evaluation_periods  = 3
  threshold           = var.ecs_memory_threshold
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}

# --- Alarms: metrics queue backlog ---

resource "aws_cloudwatch_metric_alarm" "metrics_queue_age" {
  count = var.create_alarms && var.metrics_queue_name != null ? 1 : 0

  alarm_name          = "${var.name_prefix}-metrics-queue-backlog"
  alarm_description   = "Oldest message in the metrics queue is older than threshold - processing is falling behind."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateAgeOfOldestMessage"
  dimensions          = { QueueName = var.metrics_queue_name }
  statistic           = "Maximum"
  period              = local.period
  evaluation_periods  = 2
  threshold           = var.queue_max_age_seconds
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}

# --- Alarms: API Gateway (HTTP API) ---

resource "aws_cloudwatch_metric_alarm" "api_5xx" {
  count = var.create_alarms && var.api_gateway_id != null ? 1 : 0

  alarm_name          = "${var.name_prefix}-api-5xx"
  alarm_description   = "API Gateway 5xx responses exceeded threshold."
  namespace           = "AWS/ApiGateway"
  metric_name         = "5xx"
  dimensions          = { ApiId = var.api_gateway_id }
  statistic           = "Sum"
  period              = local.period
  evaluation_periods  = 1
  threshold           = var.api_5xx_threshold
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "api_latency" {
  count = var.create_alarms && var.api_gateway_id != null ? 1 : 0

  alarm_name          = "${var.name_prefix}-api-p99-latency"
  alarm_description   = "API Gateway p99 latency is high."
  namespace           = "AWS/ApiGateway"
  metric_name         = "Latency"
  dimensions          = { ApiId = var.api_gateway_id }
  extended_statistic  = "p99"
  period              = local.period
  evaluation_periods  = 3
  threshold           = var.api_p99_latency_threshold_ms
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}

# --- Dashboard (ported from the CDK reference) ---
#
# Widgets are emitted conditionally so a metric never carries a null dimension
# value (CloudWatch rejects non-string metric fields). E.g. on the Lambda-API
# path the ECS/ALB identifiers are null, so that whole section is omitted.
# x/y are omitted on purpose - CloudWatch auto-positions widgets in order, which
# keeps the layout gap-free regardless of which sections are present.

locals {
  show_api_section = local.has_ecs || local.has_alb

  # Worker lists (null functions filtered out) drive the throughput/latency rows
  # and the scorecard, so each row is defined once and rendered per worker.
  pipeline_workers = [
    for w in [
      { title = "Document Processor", fn = var.document_processor_function_name },
      { title = "BDA Result Processor", fn = var.bda_result_processor_function_name },
    ] : w if w.fn != null
  ]
  observability_workers = [
    for w in [
      { title = "Metrics Processor", fn = var.metrics_processor_function_name },
      { title = "Metrics Aggregator", fn = var.metrics_aggregator_function_name },
    ] : w if w.fn != null
  ]
  all_workers = concat(local.pipeline_workers, local.observability_workers)

  # Scorecard metric rows (built null-safe; an empty row drops its widget).
  scorecard_dlq_metrics = concat(
    var.document_processor_dlq_name != null ? [["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", var.document_processor_dlq_name, { stat = "Maximum", label = "Doc Processor" }]] : [],
    var.bda_output_dlq_name != null ? [["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", var.bda_output_dlq_name, { stat = "Maximum", label = "BDA Output" }]] : [],
  )
  scorecard_error_metrics = [for w in local.all_workers : ["AWS/Lambda", "Errors", "FunctionName", w.fn, { stat = "Sum", label = w.title }]]
  scorecard_queue_metrics = var.metrics_queue_name != null ? [
    ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", var.metrics_queue_name, { stat = "Maximum", label = "Depth" }],
    ["AWS/SQS", "ApproximateAgeOfOldestMessage", "QueueName", var.metrics_queue_name, { stat = "Maximum", label = "Oldest (s)" }],
  ] : []
  # API Gateway's single $default route can't tell a submission from the ~16 status
  # polls that follow it, so the scorecard/graph lead with the access-log split
  # metrics (submissions vs polls) and keep 4xx/5xx from API Gateway. The metrics
  # tuple is inlined at the widget (a conditional can't carry a mixed-arity tuple).
  show_api_scorecard = var.api_log_metrics != null
  show_scorecard     = length(local.scorecard_dlq_metrics) > 0 || length(local.scorecard_error_metrics) > 0 || length(local.scorecard_queue_metrics) > 0 || local.show_api_scorecard

  dashboard_widgets = concat(
    # === Health at a glance (single-value scorecards) ===
    local.show_scorecard ? [{ type = "text", width = 24, height = 1, properties = { markdown = "## Health at a glance" } }] : [],
    local.show_api_scorecard ? [{
      type = "metric", width = 16, height = 3,
      properties = {
        title                = "API activity (sum in range)", region = var.region, view = "singleValue", period = local.period,
        setPeriodToTimeRange = true,
        metrics = [
          [var.api_log_metrics.namespace, var.api_log_metrics.submitted_metric, { stat = "Sum", label = "Documents submitted" }],
          [var.api_log_metrics.namespace, var.api_log_metrics.polls_metric, { stat = "Sum", label = "Status polls" }],
          ["AWS/ApiGateway", "4xx", "ApiId", var.api_gateway_id, { stat = "Sum", label = "4xx" }],
          ["AWS/ApiGateway", "5xx", "ApiId", var.api_gateway_id, { stat = "Sum", label = "5xx" }],
        ]
      }
    }] : [],
    length(local.scorecard_queue_metrics) > 0 ? [{
      type = "metric", width = 8, height = 3,
      properties = {
        title                = "Analytics queue (max in range)", region = var.region, view = "singleValue", period = local.period,
        setPeriodToTimeRange = true, metrics = local.scorecard_queue_metrics
      }
    }] : [],
    length(local.scorecard_error_metrics) > 0 ? [{
      type = "metric", width = 16, height = 3,
      properties = {
        title                = "Errors (sum in range)", region = var.region, view = "singleValue", period = local.period,
        setPeriodToTimeRange = true, metrics = local.scorecard_error_metrics
      }
    }] : [],
    length(local.scorecard_dlq_metrics) > 0 ? [{
      type = "metric", width = 8, height = 3,
      properties = {
        title                = "Dead-letter messages (max in range)", region = var.region, view = "singleValue", period = local.period,
        setPeriodToTimeRange = true, metrics = local.scorecard_dlq_metrics
      }
    }] : [],





    # === API (API Gateway HTTP API) ===
    # Split into single-widget conditionals: a conditional whose true branch mixes
    # differently-shaped widgets can't type-unify with the empty false branch.
    var.api_gateway_id != null ? [{ type = "text", width = 24, height = 1, properties = { markdown = "## API" } }] : [],
    var.api_gateway_id != null ? [{
      type = "metric", width = 12, height = 6,
      properties = {
        title = "API Requests and Errors", region = var.region, view = "timeSeries", period = local.period,
        metrics = [
          [var.api_log_metrics.namespace, var.api_log_metrics.submitted_metric, { stat = "Sum", label = "Documents submitted", color = "#1f77b4" }],
          [var.api_log_metrics.namespace, var.api_log_metrics.polls_metric, { stat = "Sum", label = "Status polls", color = "#9467bd" }],
          ["AWS/ApiGateway", "4xx", "ApiId", var.api_gateway_id, { stat = "Sum", label = "4xx", color = "#ff7f0e", yAxis = "right" }],
          ["AWS/ApiGateway", "5xx", "ApiId", var.api_gateway_id, { stat = "Sum", label = "5xx", color = "#d62728", yAxis = "right" }],
        ]
        yAxis = { right = { min = 0, label = "errors", showUnits = false } }
      }
    }] : [],
    var.api_gateway_id != null ? [{
      type = "metric", width = 12, height = 6,
      properties = {
        title = "API Latency", region = var.region, view = "timeSeries", period = local.period,
        metrics = [
          ["AWS/ApiGateway", "Latency", "ApiId", var.api_gateway_id, { stat = "p50", label = "p50" }],
          ["AWS/ApiGateway", "Latency", "ApiId", var.api_gateway_id, { stat = "p99", label = "p99" }],
          ["AWS/ApiGateway", "IntegrationLatency", "ApiId", var.api_gateway_id, { stat = "p99", label = "Integration p99" }],
        ]
        yAxis = { left = { label = "ms", showUnits = false } }
      }
    }] : [],

    # === ECS / API ===
    local.show_api_section ? [{ type = "text", width = 24, height = 1, properties = { markdown = "## ECS / API" } }] : [],
    local.has_ecs ? [
      {
        type = "metric", width = 6, height = 6,
        properties = {
          title   = "Running Tasks", region = var.region, view = "timeSeries", period = local.period,
          metrics = [["ECS/ContainerInsights", "RunningTaskCount", "ClusterName", var.ecs_cluster_name, "ServiceName", var.ecs_service_name, { stat = "Average" }]]
        }
      },
      {
        type = "metric", width = 6, height = 6,
        properties = {
          title   = "ECS CPU Utilization", region = var.region, view = "timeSeries", period = local.period,
          metrics = [["AWS/ECS", "CPUUtilization", "ClusterName", var.ecs_cluster_name, "ServiceName", var.ecs_service_name, { stat = "Average" }]]
        }
      },
      {
        type = "metric", width = 6, height = 6,
        properties = {
          title   = "ECS Memory Utilization", region = var.region, view = "timeSeries", period = local.period,
          metrics = [["AWS/ECS", "MemoryUtilization", "ClusterName", var.ecs_cluster_name, "ServiceName", var.ecs_service_name, { stat = "Average" }]]
        }
      },
    ] : [],
    local.has_alb ? [
      {
        type = "metric", width = 6, height = 6,
        properties = {
          title = "ALB 5xx Errors", region = var.region, view = "timeSeries", period = local.period, stat = "Sum",
          metrics = [
            ["AWS/ApplicationELB", "HTTPCode_ELB_5XX_Count", "LoadBalancer", var.alb_arn_suffix],
            ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", "LoadBalancer", var.alb_arn_suffix, "TargetGroup", var.target_group_arn_suffix],
          ]
        }
      },
    ] : [],

    # === Pipeline Health: throughput + error rate % (metric math) ===
    length(local.pipeline_workers) > 0 ? [{ type = "text", width = 24, height = 1, properties = { markdown = "## Pipeline Health" } }] : [],
    [for w in local.pipeline_workers : {
      type = "metric", width = 12, height = 6,
      properties = {
        title = "${w.title} - throughput and error rate", region = var.region, view = "timeSeries", period = local.period,
        metrics = [
          ["AWS/Lambda", "Invocations", "FunctionName", w.fn, { stat = "Sum", id = "inv", label = "Invocations", color = "#1f77b4" }],
          ["AWS/Lambda", "Errors", "FunctionName", w.fn, { stat = "Sum", id = "err", visible = false }],
          [{ expression = "100*err/inv", label = "Error rate %", id = "rate", yAxis = "right", color = "#d62728" }],
        ]
        yAxis = { right = { min = 0, label = "%", showUnits = false } }
      }
    }],

    # === Pipeline Latency: p50/p99/max with timeout reference line ===
    length(local.pipeline_workers) > 0 ? [{ type = "text", width = 24, height = 1, properties = { markdown = "## Pipeline Latency" } }] : [],
    [for w in local.pipeline_workers : {
      type = "metric", width = 12, height = 6,
      properties = {
        title = "${w.title} Duration", region = var.region, view = "timeSeries", period = local.period,
        metrics = [
          ["AWS/Lambda", "Duration", "FunctionName", w.fn, { stat = "p50", label = "p50" }],
          ["AWS/Lambda", "Duration", "FunctionName", w.fn, { stat = "p99", label = "p99" }],
          ["AWS/Lambda", "Duration", "FunctionName", w.fn, { stat = "Maximum", label = "Max" }],
        ]
        # Auto-scaled axis shows latency trend; the "near timeout" threshold is
        # covered by the duration alarm rather than a reference line that would
        # dwarf actual durations.
        yAxis = { left = { label = "ms", showUnits = false } }
      }
    }],

    # === Queues ===
    var.metrics_queue_name != null ? [
      { type = "text", width = 24, height = 1, properties = { markdown = "## Queues" } },
    ] : [],
    var.metrics_queue_name != null ? [
      {
        type = "metric", width = 12, height = 6,
        properties = {
          title   = "Analytics Queue Depth", region = var.region, view = "timeSeries", period = local.period,
          metrics = [["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", var.metrics_queue_name, { stat = "Maximum", label = "Messages Visible" }]]
        }
      },
      {
        type = "metric", width = 12, height = 6,
        properties = {
          title   = "Analytics Queue - Age of Oldest Message", region = var.region, view = "timeSeries", period = local.period,
          metrics = [["AWS/SQS", "ApproximateAgeOfOldestMessage", "QueueName", var.metrics_queue_name, { stat = "Maximum", label = "Oldest Message Age" }]]
        }
      },
    ] : [],

    # === Dead Letter Queues ===
    length(local.scorecard_dlq_metrics) > 0 ? [{ type = "text", width = 24, height = 1, properties = { markdown = "## Dead Letter Queues" } }] : [],
    var.document_processor_dlq_name != null ? [
      {
        type = "metric", width = 12, height = 6,
        properties = {
          title   = "Document Processor DLQ", region = var.region, view = "timeSeries", period = local.period,
          metrics = [["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", var.document_processor_dlq_name, { stat = "Maximum", label = "Messages Visible" }]]
        }
      },
    ] : [],
    var.bda_output_dlq_name != null ? [
      {
        type = "metric", width = 12, height = 6,
        properties = {
          title   = "BDA Output DLQ", region = var.region, view = "timeSeries", period = local.period,
          metrics = [["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", var.bda_output_dlq_name, { stat = "Maximum", label = "Messages Visible" }]]
        }
      },
    ] : [],

    # === Observability Lambdas: throughput + error rate % ===
    length(local.observability_workers) > 0 ? [{ type = "text", width = 24, height = 1, properties = { markdown = "## Observability Lambdas" } }] : [],
    [for w in local.observability_workers : {
      type = "metric", width = 12, height = 6,
      properties = {
        title = "${w.title} - throughput and error rate", region = var.region, view = "timeSeries", period = local.period,
        metrics = [
          ["AWS/Lambda", "Invocations", "FunctionName", w.fn, { stat = "Sum", id = "inv", label = "Invocations", color = "#1f77b4" }],
          ["AWS/Lambda", "Errors", "FunctionName", w.fn, { stat = "Sum", id = "err", visible = false }],
          [{ expression = "100*err/inv", label = "Error rate %", id = "rate", yAxis = "right", color = "#d62728" }],
        ]
        yAxis = { right = { min = 0, label = "%", showUnits = false } }
      }
    }],
  )

  dashboard_body = jsonencode({ widgets = local.dashboard_widgets })
}

resource "aws_cloudwatch_dashboard" "this" {
  count          = var.create_dashboard ? 1 : 0
  dashboard_name = "${var.name_prefix}-dashboard"
  dashboard_body = local.dashboard_body
}

# --- Outputs ---

output "sns_topic_arn" {
  value = aws_sns_topic.alarms.arn
}
