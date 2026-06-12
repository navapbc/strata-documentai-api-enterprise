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
    workspace_id = string
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
