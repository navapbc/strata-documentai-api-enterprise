variable "name" {
  type        = string
  description = "Name of the S3 bucket."
}

variable "is_temporary" {
  type        = bool
  description = "When true, marks resources as ephemeral so they can be force-destroyed."
  default     = false
}

variable "service_principals_with_access" {
  type        = list(string)
  description = "AWS service principals granted access to the bucket via its policy."
  default     = []
}

variable "versioning_status" {
  type        = string
  description = "The versioning state of the bucket."
  default     = "Disabled" # Default to Disabled, set to "Enabled" if versioning is desired

  validation {
    condition     = contains(["Enabled", "Disabled", "Suspended"], var.versioning_status)
    error_message = "versioning_status must be Enabled, Disabled, or Suspended."
  }
}

variable "lifecycle_rules" {
  type = list(object({
    id                         = string
    prefix                     = optional(string, "")
    expiration_days            = optional(number)
    transition_to_ia_days      = optional(number)
    transition_to_glacier_days = optional(number)
  }))
  description = "Lifecycle rules for object expiration and storage-class transitions."
  default     = []
}
