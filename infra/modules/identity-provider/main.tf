# Cognito User Pool + App Client for console authentication

variable "name" {
  type = string
}

variable "is_temporary" {
  type    = bool
  default = false
}

variable "callback_urls" {
  type    = list(string)
  default = []
}

variable "logout_urls" {
  type    = list(string)
  default = []
}

variable "password_minimum_length" {
  type    = number
  default = 12
}

variable "temporary_password_validity_days" {
  type    = number
  default = 7
}

variable "domain_identity_arn" {
  type        = string
  description = "SES domain identity ARN for sending emails. If null, uses Cognito default."
  default     = null
}

variable "sender_email" {
  type    = string
  default = null
}

variable "sender_display_name" {
  type    = string
  default = null
}

variable "reply_to_email" {
  type    = string
  default = null
}

variable "verification_email_message" {
  type    = string
  default = null
}

variable "verification_email_subject" {
  type    = string
  default = null
}

# --- Cognito User Pool ---

resource "aws_cognito_user_pool" "this" {
  name = var.name

  deletion_protection = var.is_temporary ? "INACTIVE" : "ACTIVE"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  device_configuration {
    challenge_required_on_new_device      = true
    device_only_remembered_on_user_prompt = true
  }

  email_configuration {
    source_arn             = var.domain_identity_arn
    email_sending_account  = var.domain_identity_arn != null ? "DEVELOPER" : "COGNITO_DEFAULT"
    from_email_address     = var.domain_identity_arn != null ? (var.sender_display_name != null ? "${var.sender_display_name} <${var.sender_email}>" : var.sender_email) : null
    reply_to_email_address = var.reply_to_email
  }

  password_policy {
    minimum_length                   = var.password_minimum_length
    temporary_password_validity_days = var.temporary_password_validity_days
  }

  mfa_configuration = "OPTIONAL"
  software_token_mfa_configuration {
    enabled = true
  }

  user_pool_add_ons {
    advanced_security_mode = "AUDIT"
  }

  username_configuration {
    case_sensitive = false
  }

  user_attribute_update_settings {
    attributes_require_verification_before_update = ["email"]
  }

  schema {
    name                = "email"
    attribute_data_type = "String"
    mutable             = true
    required            = true

    string_attribute_constraints {
      max_length = 2048
      min_length = 0
    }
  }

  # Custom attribute: tenant the user belongs to (set by super-admin on approval).
  # Mutable so super-admins can re-assign users to a different tenant.
  schema {
    name                = "tenant_id"
    attribute_data_type = "String"
    mutable             = true
    required            = false

    string_attribute_constraints {
      max_length = 128
      min_length = 1
    }
  }

  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_message        = var.verification_email_message
    email_subject        = var.verification_email_subject
  }
}

# --- App Client ---

resource "aws_cognito_user_pool_client" "this" {
  name         = "${var.name}-client"
  user_pool_id = aws_cognito_user_pool.this.id

  callback_urls                = var.callback_urls
  logout_urls                  = var.logout_urls
  supported_identity_providers = ["COGNITO"]

  refresh_token_validity = 1
  access_token_validity  = 60
  id_token_validity      = 60

  token_validity_units {
    refresh_token = "days"
    access_token  = "minutes"
    id_token      = "minutes"
  }

  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["phone", "email", "openid", "profile"]
  explicit_auth_flows                  = ["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]

  prevent_user_existence_errors = "ENABLED"

  enable_token_revocation                       = true
  enable_propagate_additional_user_context_data = false

  read_attributes = ["email", "email_verified", "phone_number", "phone_number_verified", "updated_at", "custom:tenant_id"]
  # tenant_id is intentionally NOT in write_attributes — users must not set their
  # own tenant. It's written via AdminUpdateUserAttributes from the backend.
  write_attributes = ["email", "updated_at", "phone_number"]
}

# --- Cognito Groups (roles) ---

resource "aws_cognito_user_group" "super_admin" {
  name         = "super-admin"
  user_pool_id = aws_cognito_user_pool.this.id
  description  = "Full cross-tenant access. Can approve users and manage roles."
  precedence   = 1
}

resource "aws_cognito_user_group" "tenant_admin" {
  name         = "tenant-admin"
  user_pool_id = aws_cognito_user_pool.this.id
  description  = "Scoped to a single tenant. Can manage API keys for that tenant."
  precedence   = 10
}

# --- Store client secret in SSM ---

resource "aws_ssm_parameter" "client_secret" {
  name  = "/${var.name}/identity-provider/client-secret"
  type  = "SecureString"
  value = aws_cognito_user_pool_client.this.client_secret
}

# --- IAM Policy ---

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

data "aws_iam_policy_document" "access" {
  statement {
    actions   = ["cognito-idp:*"]
    effect    = "Allow"
    resources = ["arn:aws:cognito-idp:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:userpool/${aws_cognito_user_pool.this.id}"]
  }
}

resource "aws_iam_policy" "access" {
  name   = "${var.name}-cognito-access"
  policy = data.aws_iam_policy_document.access.json
}

# --- Outputs ---

output "user_pool_id" {
  value = aws_cognito_user_pool.this.id
}

output "client_id" {
  value = aws_cognito_user_pool_client.this.id
}

output "client_secret_arn" {
  value = aws_ssm_parameter.client_secret.arn
}

output "access_policy_arn" {
  value = aws_iam_policy.access.arn
}
