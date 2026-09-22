variable "name" {
  type        = string
  description = "Base name for the Bedrock Data Automation project and its blueprints."
}

variable "description" {
  type        = string
  description = "Human-readable description for the BDA project."
  default     = null
}

variable "blueprint_file_paths" {
  type        = list(string)
  description = "Local file paths of custom blueprint schemas to create and attach to the project."
  default     = []
}

variable "blueprint_arns" {
  type        = list(string)
  description = "ARNs of existing blueprints to attach to the project."
  default     = []
}

variable "standard_output_configuration" {
  type        = any
  description = "Optional standard output configuration object for the BDA project. When null, BDA defaults are used."
  default     = null
}

variable "tags" {
  type        = map(string)
  description = "Additional tags applied to BDA resources."
  default     = {}
}
