variable "name" {
  type        = string
  description = "Base name for the Bedrock Data Automation project and its blueprints."
}

variable "blueprints" {
  type        = list(string)
  description = "List of blueprint file paths or ARNs to attach to the project."
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
