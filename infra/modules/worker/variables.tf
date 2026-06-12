# Lambda worker module
# S3 event → EventBridge → Lambda (with DLQ on EventBridge rule)

variable "function_name" {
  type        = string
  description = "Name of the Lambda worker function."
}

variable "image_uri" {
  type        = string
  description = "ECR container image URI (including tag) for the worker."
}

variable "command" {
  type        = list(string)
  description = "CMD override for the container (Lambda handler entrypoint)."
}

variable "timeout" {
  type        = number
  description = "Lambda function timeout in seconds (1-900)."
  default     = 300

  validation {
    condition     = var.timeout >= 1 && var.timeout <= 900
    error_message = "timeout must be between 1 and 900 seconds (the Lambda maximum)."
  }
}

variable "memory_size" {
  type        = number
  description = "Lambda memory allocation in MB (128-10240)."
  default     = 512

  validation {
    condition     = var.memory_size >= 128 && var.memory_size <= 10240
    error_message = "memory_size must be between 128 and 10240 MB."
  }
}

variable "environment_variables" {
  type        = map(string)
  description = "Environment variables passed to the worker."
  default     = {}
}

variable "policy_arns" {
  type        = map(string)
  description = "IAM policy ARNs to attach to the Lambda execution role."
  default     = {}
}

variable "s3_trigger" {
  type = object({
    source_bucket = string
    path_prefix   = string
  })
  description = "S3 event trigger config routed through EventBridge. Null disables the S3 trigger."
  default     = null
}

variable "sqs_trigger" {
  type = object({
    queue_arn                   = string
    batch_size                  = optional(number, 10)
    max_batching_window_seconds = optional(number, 300)
  })
  description = "SQS queue trigger config. Null disables the SQS trigger."
  default     = null
}

variable "schedules" {
  type = list(object({
    name                = string
    schedule_expression = string
    input               = optional(map(string))
  }))
  description = "EventBridge schedules with optional input payloads."
  default     = []
}

variable "vpc_config" {
  type = object({
    subnet_ids         = list(string)
    security_group_ids = list(string)
  })
  description = "Optional VPC configuration for the worker. When null, the function runs outside a VPC."
  default     = null
}
