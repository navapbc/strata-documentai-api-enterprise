variable "name" {
  type        = string
  description = "Base name used to prefix analytics resources (Glue database/table, Athena workgroup, IAM policy)."
}

variable "results_bucket_name" {
  type        = string
  description = "Name of the S3 bucket where Athena query results are written."
}

variable "metrics_bucket_name" {
  type        = string
  description = "S3 bucket where raw DDB export data lands (source for Athena queries)."
}

variable "is_temporary" {
  type        = bool
  description = "When true, marks resources as ephemeral so they can be force-destroyed (e.g. for ephemeral environments)."
  default     = false
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
