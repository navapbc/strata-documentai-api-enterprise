# API Gateway HTTP API → Lambda (container image)

variable "function_name" {
  type        = string
  description = "Name of the Lambda function fronted by the HTTP API."
}

variable "image_uri" {
  type        = string
  description = "ECR container image URI (including tag) for the Lambda function."
}

variable "command" {
  type        = list(string)
  description = "CMD override for the Lambda container."
  default     = ["documentai_api.app.handler"]
}

variable "timeout" {
  type        = number
  description = "Lambda function timeout in seconds (1-900)."
  default     = 30

  validation {
    condition     = var.timeout >= 1 && var.timeout <= 900
    error_message = "timeout must be between 1 and 900 seconds (the Lambda maximum)."
  }
}

variable "memory_size" {
  type        = number
  description = "Lambda memory allocation in MB (128-10240)."
  default     = 1024

  validation {
    condition     = var.memory_size >= 128 && var.memory_size <= 10240
    error_message = "memory_size must be between 128 and 10240 MB."
  }
}

variable "environment_variables" {
  type        = map(string)
  description = "Environment variables passed to the Lambda function."
  default     = {}
}

variable "policy_arns" {
  type        = map(string)
  description = "Map of IAM policy ARNs to attach to the Lambda execution role."
  default     = {}
}

variable "vpc_config" {
  type = object({
    subnet_ids         = list(string)
    security_group_ids = list(string)
  })
  description = "Optional VPC configuration for the Lambda function. When null, the function runs outside a VPC."
  default     = null
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
