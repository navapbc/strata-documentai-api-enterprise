variable "parameters" {
  type        = map(string)
  description = "Map of SSM parameter name (relative to prefix) to value."
  default     = {}
}

variable "prefix" {
  type        = string
  description = "SSM parameter path prefix (e.g. /docai/dev)."
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
