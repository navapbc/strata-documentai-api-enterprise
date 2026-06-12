variable "name" {
  type        = string
  description = "Name of the ECR repository."
}

variable "image_tag_mutability" {
  type        = string
  description = "Whether image tags can be overwritten. One of MUTABLE or IMMUTABLE."
  default     = "MUTABLE"

  validation {
    condition     = contains(["MUTABLE", "IMMUTABLE"], var.image_tag_mutability)
    error_message = "image_tag_mutability must be MUTABLE or IMMUTABLE."
  }
}

variable "max_image_count" {
  type        = number
  description = "Number of most-recent images to retain; older images are expired by lifecycle policy."
  default     = 10

  validation {
    condition     = var.max_image_count >= 1
    error_message = "max_image_count must be at least 1."
  }
}
