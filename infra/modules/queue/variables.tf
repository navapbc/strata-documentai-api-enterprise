variable "name" {
  type        = string
  description = "Base name for the SQS queue and its dead-letter queue."
}

variable "visibility_timeout_seconds" {
  type        = number
  description = "Visibility timeout for in-flight messages, in seconds."
  default     = 300
}

variable "message_retention_seconds" {
  type        = number
  description = "How long messages are retained in the main queue, in seconds."
  default     = 86400 # 1 day
}

variable "max_receive_count" {
  type        = number
  description = "Number of receives before a message is moved to the dead-letter queue."
  default     = 3

  validation {
    condition     = var.max_receive_count >= 1
    error_message = "max_receive_count must be at least 1."
  }
}

variable "dlq_retention_seconds" {
  type        = number
  description = "How long messages are retained in the dead-letter queue, in seconds."
  default     = 1209600 # 14 days
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
