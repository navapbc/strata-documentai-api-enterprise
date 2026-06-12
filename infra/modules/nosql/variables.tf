variable "table_name" {
  type        = string
  description = "Name of the DynamoDB table."
}

variable "hash_key" {
  type        = string
  description = "Name of the table partition (hash) key attribute."
  default     = "id"
}

variable "hash_key_type" {
  type        = string
  description = "Attribute type of the hash key: S (string), N (number), or B (binary)."
  default     = "S"

  validation {
    condition     = contains(["S", "N", "B"], var.hash_key_type)
    error_message = "hash_key_type must be S, N, or B."
  }
}

variable "sort_key" {
  type        = string
  description = "Name of the table sort (range) key attribute. Null for a table with no sort key."
  default     = null
}

variable "sort_key_type" {
  type        = string
  description = "Attribute type of the sort key: S (string), N (number), or B (binary)."
  default     = "S"

  validation {
    condition     = contains(["S", "N", "B"], var.sort_key_type)
    error_message = "sort_key_type must be S, N, or B."
  }
}

variable "ttl_attribute" {
  type        = string
  description = "Attribute used for DynamoDB TTL expiry. Null disables TTL."
  default     = null
}

variable "global_secondary_indexes" {
  type = list(object({
    name            = string
    hash_key        = string
    hash_key_type   = string
    sort_key        = optional(string)
    sort_key_type   = optional(string)
    projection_type = optional(string, "ALL")
  }))
  description = "Global secondary indexes to create on the table."
  default     = []
}

variable "is_temporary" {
  type        = bool
  description = "When true, marks resources as ephemeral so they can be force-destroyed."
  default     = false
}
