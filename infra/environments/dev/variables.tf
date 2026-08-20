variable "project_name" {
  type    = string
  default = "docai"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "bda_region" {
  type    = string
  default = "us-east-1"
}

variable "image_tag" {
  type        = string
  description = "Container image tag to deploy"
  default     = "latest"
}

variable "alarm_emails" {
  type        = list(string)
  description = "Email addresses subscribed to the alarm SNS topic (set per-env, prd only)"
  default     = []
}

variable "slack_config" {
  type = object({
    workspace_id = string
    channel_id   = string
  })
  description = "Optional AWS Chatbot Slack target for alarms. Requires a one-time workspace authorization in the console."
  default     = null
}

variable "google_sso_enabled" {
  type        = bool
  description = "Enable Google SSO. Requires SSM params /{project}/{env}/google-oauth-client-id and google-oauth-client-secret to be pre-created."
  default     = true
}

variable "google_allowed_domains" {
  type        = list(string)
  description = "Email domains allowed for Google SSO (e.g. ['example.com']). Empty list allows all domains."
  default     = []
}

variable "otel_enabled" {
  type        = bool
  description = "Enable OpenTelemetry tracing. Set to true and provide otel_exporter_otlp_endpoint to activate."
  default     = true
}
variable "otel_service_name" {
  type        = string
  description = "OTEL service name reported in traces."
  default     = "documentai-api"
}

variable "otel_exporter_otlp_endpoint" {
  type        = string
  description = "OTLP gRPC collector endpoint (e.g. http://adot-collector:4317)."
  default     = "http://localhost:4317"
}

variable "extra_cors_allowed_origins" {
  type        = list(string)
  description = "Additional CORS origins beyond the managed admin/demo CloudFront URLs (e.g. ['http://localhost:3000'] for local UI dev). Inject at plan/apply via -var or TF_VAR_extra_cors_allowed_origins; the CloudFront origins are always included automatically."
  default     = []
}
