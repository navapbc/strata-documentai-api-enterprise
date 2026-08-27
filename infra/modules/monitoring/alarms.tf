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

  alarm_name          = "${each.key}-errors"
  alarm_description   = "Lambda ${each.key} reported errors."
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = each.key }
  statistic           = "Sum"
  period              = local.period
  evaluation_periods  = 1
  threshold           = var.lambda_error_threshold
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  for_each = local.alarm_worker_names

  alarm_name          = "${each.key}-throttles"
  alarm_description   = "Lambda ${each.key} is being throttled."
  namespace           = "AWS/Lambda"
  metric_name         = "Throttles"
  dimensions          = { FunctionName = each.key }
  statistic           = "Sum"
  period              = local.period
  evaluation_periods  = var.lambda_throttle_evaluation_periods
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  for_each = local.alarm_worker_names

  alarm_name          = "${each.key}-duration-near-timeout"
  alarm_description   = "Lambda ${each.key} max duration exceeded 80% of its timeout."
  namespace           = "AWS/Lambda"
  metric_name         = "Duration"
  dimensions          = { FunctionName = each.key }
  statistic           = "Maximum"
  period              = local.period
  evaluation_periods  = var.lambda_duration_evaluation_periods
  threshold           = each.value
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

# --- Alarms: API Lambda ---

locals {
  api_lambda_duration_threshold_ms = var.api_lambda_timeout_seconds * 1000 * 0.8
}

resource "aws_cloudwatch_metric_alarm" "api_lambda_errors" {
  count = var.create_alarms && var.api_lambda_function_name != null ? 1 : 0

  alarm_name          = "${var.api_lambda_function_name}-errors"
  alarm_description   = "API Lambda ${var.api_lambda_function_name} reported errors."
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = var.api_lambda_function_name }
  statistic           = "Sum"
  period              = local.period
  evaluation_periods  = 1
  threshold           = var.lambda_error_threshold
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "api_lambda_throttles" {
  count = var.create_alarms && var.api_lambda_function_name != null ? 1 : 0

  alarm_name          = "${var.api_lambda_function_name}-throttles"
  alarm_description   = "API Lambda ${var.api_lambda_function_name} is being throttled."
  namespace           = "AWS/Lambda"
  metric_name         = "Throttles"
  dimensions          = { FunctionName = var.api_lambda_function_name }
  statistic           = "Sum"
  period              = local.period
  evaluation_periods  = var.lambda_throttle_evaluation_periods
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "api_lambda_duration" {
  count = var.create_alarms && var.api_lambda_function_name != null ? 1 : 0

  alarm_name          = "${var.api_lambda_function_name}-duration-near-timeout"
  alarm_description   = "API Lambda ${var.api_lambda_function_name} max duration exceeded 80% of its timeout."
  namespace           = "AWS/Lambda"
  metric_name         = "Duration"
  dimensions          = { FunctionName = var.api_lambda_function_name }
  statistic           = "Maximum"
  period              = local.period
  evaluation_periods  = var.lambda_duration_evaluation_periods
  threshold           = local.api_lambda_duration_threshold_ms
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}

# --- Alarms: scheduled worker missing invocations ---

resource "aws_cloudwatch_metric_alarm" "scheduled_worker_no_invocations" {
  for_each = local.alarm_scheduled_workers

  alarm_name          = "${each.key}-no-invocations"
  alarm_description   = "Scheduled Lambda ${each.key} has not been invoked recently - EventBridge rule or permission may be broken."
  namespace           = "AWS/Lambda"
  metric_name         = "Invocations"
  dimensions          = { FunctionName = each.key }
  statistic           = "Sum"
  period              = each.value
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
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
