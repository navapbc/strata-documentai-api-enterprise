# Cognito User Pool + App Client for console authentication

variable "name" {
  type        = string
  description = "Base name for the Cognito user pool and related resources."
}

variable "is_temporary" {
  type        = bool
  description = "When true, marks resources as ephemeral so they can be force-destroyed."
  default     = false
}

variable "callback_urls" {
  type        = list(string)
  description = "Allowed OAuth callback URLs for the app client."
  default     = []
}

variable "logout_urls" {
  type        = list(string)
  description = "Allowed OAuth logout URLs for the app client."
  default     = []
}

variable "password_minimum_length" {
  type        = number
  description = "Minimum password length for the user pool policy (Cognito allows 6-99)."
  default     = 12

  validation {
    condition     = var.password_minimum_length >= 6 && var.password_minimum_length <= 99
    error_message = "password_minimum_length must be between 6 and 99 (Cognito limits)."
  }
}

variable "temporary_password_validity_days" {
  type        = number
  description = "Number of days an admin-created temporary password remains valid."
  default     = 7

  validation {
    condition     = var.temporary_password_validity_days >= 0
    error_message = "temporary_password_validity_days must be zero or positive."
  }
}

variable "domain_identity_arn" {
  type        = string
  description = "SES domain identity ARN for sending emails. If null, uses the Cognito default email facility."
  default     = null
}

variable "sender_email" {
  type        = string
  description = "From address for Cognito emails when using SES. Required if domain_identity_arn is set."
  default     = null
}

variable "sender_display_name" {
  type        = string
  description = "Display name shown on Cognito emails sent via SES."
  default     = null
}

variable "reply_to_email" {
  type        = string
  description = "Reply-To address for Cognito emails."
  default     = null
}

variable "verification_email_message" {
  type        = string
  description = "Custom body for the account verification email. Uses the Cognito default when null."
  default     = null
}

variable "verification_email_subject" {
  type        = string
  description = "Custom subject for the account verification email. Uses the Cognito default when null."
  default     = null
}

variable "google_client_id" {
  type        = string
  description = "Google OAuth 2.0 client ID. When set, enables Google as a federated identity provider. Store in SSM and pass via data source — never commit to the repo."
  default     = null
}

variable "google_client_secret" {
  type        = string
  description = "Google OAuth 2.0 client secret. Store in SSM and pass via data source — never commit to the repo."
  default     = null
  sensitive   = true
}

variable "google_client_id_ssm_param" {
  type        = string
  description = "SSM parameter name containing the Google client ID. Used instead of google_client_id when you want to read the value from SSM at plan time."
  default     = null
}

variable "google_client_secret_ssm_param" {
  type        = string
  description = "SSM parameter name containing the Google client secret. Used instead of google_client_secret when you want to read the value from SSM at plan time."
  default     = null
}

variable "google_allowed_domains" {
  type        = list(string)
  description = "Email domains allowed for Google SSO (e.g. ['example.com']). Empty list allows all domains."
  default     = []
}
