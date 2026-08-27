variable "name_prefix" {
  type        = string
  description = "Prefix for topic/alarm names, e.g. docai-prd-<account>"
}

variable "project_name" {
  type        = string
  description = "Project name used in the dashboard name (no account ID)."
}

variable "environment" {
  type        = string
  description = "Environment name used in the dashboard name (e.g. dev, prd)."
}

variable "region" {
  type        = string
  description = "Region for dashboard widget metrics"
}

variable "create_alarms" {
  type        = bool
  description = "Whether to create CloudWatch alarms and the SNS notification topic."
  default     = false
}

variable "create_dashboard" {
  type        = bool
  description = "Whether to create the CloudWatch dashboard."
  default     = true
}

# --- Notification endpoints ---

variable "alarm_emails" {
  type        = list(string)
  description = "Email addresses to subscribe to the alarm SNS topic"
  default     = []
}

variable "slack" {
  type = object({
    workspace_id = string
    channel_id   = string
  })
  description = "Optional AWS Chatbot Slack target. Requires a one-time workspace authorization in the console."
  default     = null
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

variable "workers" {
  type = map(object({
    function_name             = string
    timeout_seconds           = number
    pipeline                  = bool
    scheduled                 = bool
    invocation_window_seconds = optional(number)
  }))
  description = <<-EOT
    Worker Lambdas to monitor, keyed by a stable logical name (e.g. "document-processor").
    function_name             - Lambda function name (dimension value).
    timeout_seconds           - Actual configured Lambda timeout; duration alarm fires at 80% of this.
    pipeline                  - true = Pipeline Health/Latency sections; false = Observability Lambdas section.
    scheduled                 - true = missing-invocations alarm with treat_missing_data = breaching.
    invocation_window_seconds - Required when scheduled = true. Period for the missing-invocations alarm;
                                 must be wider than the longest gap between scheduled runs
                                 (e.g. 600 for every-5-min, 86400 for daily).
  EOT
  default     = {}
}

variable "api_lambda_function_name" {
  type        = string
  description = "Name of the API Lambda to monitor. Null disables its alarms and dashboard widgets."
  default     = null
}

variable "api_lambda_timeout_seconds" {
  type        = number
  description = "Configured timeout for the API Lambda; duration alarm fires at 80% of this."
  default     = 30
}

# --- Queues ---

variable "metrics_queue_name" {
  type        = string
  description = "Name of the metrics SQS queue to monitor. Null disables its metrics."
  default     = null
}

variable "metrics_queue_dlq_name" {
  type        = string
  description = "Name of the metrics queue dead-letter queue to monitor. Null disables its alarm."
  default     = null
}

variable "document_processor_dlq_name" {
  type        = string
  description = "Name of the document-processor dead-letter queue to monitor. Null disables its metrics."
  default     = null
}

variable "bda_output_dlq_name" {
  type        = string
  description = "Name of the BDA output dead-letter queue to monitor. Null disables its metrics."
  default     = null
}

# --- Alarm thresholds ---

variable "queue_max_age_seconds" {
  type        = number
  description = "Age of the oldest queue message (seconds) that triggers an alarm."
  default     = 900
}

variable "lambda_error_threshold" {
  type        = number
  description = "Lambda error count in one period that triggers an alarm."
  default     = 3
}

variable "lambda_throttle_evaluation_periods" {
  type        = number
  description = "Consecutive periods of throttling before an alarm fires."
  default     = 2
}

variable "lambda_duration_evaluation_periods" {
  type        = number
  description = "Consecutive periods of near-timeout duration before an alarm fires."
  default     = 3
}

variable "api_5xx_threshold" {
  type        = number
  description = "API Gateway 5xx count over the evaluation period that triggers an alarm."
  default     = 5
}

variable "api_p99_latency_threshold_ms" {
  type        = number
  description = "API Gateway p99 integration latency (milliseconds) that triggers an alarm."
  default     = 3000
}
