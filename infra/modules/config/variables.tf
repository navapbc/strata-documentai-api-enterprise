variable "parameters" {
  type        = map(string)
  description = "Map of SSM parameter name (relative to prefix) to value."
  default     = {}
}

variable "prefix" {
  type        = string
  description = "SSM parameter path prefix (e.g. /docai/dev)."
}

variable "allowed_patterns" {
  type        = map(string)
  description = "Optional map of parameter key to allowed_pattern regex. Restricts values at the AWS API level."
  default     = {}
}
