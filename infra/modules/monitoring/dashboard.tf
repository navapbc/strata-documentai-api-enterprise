# Dashboard layout ported from the CDK reference
# (idp-platform-copa-v2/lib/stacks/cloudwatch-dashboard-stack.ts).
#
# Widgets are emitted conditionally so a metric never carries a null dimension
# value (CloudWatch rejects non-string metric fields). E.g. on the Lambda-API
# path the ECS/ALB identifiers are null, so that whole section is omitted.
# x/y are omitted on purpose - CloudWatch auto-positions widgets in order, which
# keeps the layout gap-free regardless of which sections are present.

locals {
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

    # === Pipeline Health: throughput and error rate % (metric math) ===
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

    # === Pipeline Latency: p50/p99/max ===
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

    # === Observability Lambdas: throughput and error rate % ===
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
