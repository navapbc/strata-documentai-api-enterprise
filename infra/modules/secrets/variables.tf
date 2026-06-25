variable "secrets" {
  type = map(object({
    manage_method     = string # "generated" or "manual"
    secret_store_name = string
  }))
  description = "Map of secret configurations"

  validation {
    condition     = alltrue([for s in values(var.secrets) : contains(["manual", "generated"], s.manage_method)])
    error_message = "manage_method must be 'manual' or 'generated'"
  }
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
