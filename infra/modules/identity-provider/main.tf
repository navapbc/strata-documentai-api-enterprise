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

  # MFA: set to "ON" in production to enforce TOTP for all users
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

  dynamic "lambda_config" {
    for_each = local.domain_restriction_enabled ? [1] : []
    content {
      pre_sign_up = aws_lambda_function.pre_signup[0].arn
    }
  }
}

# --- App Client ---

# --- Google OAuth credentials (resolved from SSM or direct variable) ---

data "aws_ssm_parameter" "google_client_id" {
  count = var.google_client_id_ssm_param != null ? 1 : 0
  name  = var.google_client_id_ssm_param
}

data "aws_ssm_parameter" "google_client_secret" {
  count = var.google_client_secret_ssm_param != null ? 1 : 0
  name  = var.google_client_secret_ssm_param
}

locals {
  resolved_google_client_id = coalesce(
    var.google_client_id,
    try(data.aws_ssm_parameter.google_client_id[0].value, null),
  )
  resolved_google_client_secret = coalesce(
    var.google_client_secret,
    try(data.aws_ssm_parameter.google_client_secret[0].value, null),
  )
  google_enabled = local.resolved_google_client_id != null
}

resource "aws_cognito_user_pool_client" "this" {
  name         = "${var.name}-client"
  user_pool_id = aws_cognito_user_pool.this.id

  callback_urls                = var.callback_urls
  logout_urls                  = var.logout_urls
  supported_identity_providers = local.google_enabled ? ["COGNITO", "Google"] : ["COGNITO"]

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
  # tenant_id is intentionally NOT in write_attributes - users must not set their
  # own tenant. It's written via AdminUpdateUserAttributes from the backend.
  write_attributes = ["email", "updated_at", "phone_number"]

  depends_on = [aws_cognito_identity_provider.google]
}

# --- Google Identity Provider (conditional) ---

resource "aws_cognito_user_pool_domain" "this" {
  count        = local.google_enabled ? 1 : 0
  domain       = "${var.name}-auth"
  user_pool_id = aws_cognito_user_pool.this.id
}

resource "aws_cognito_identity_provider" "google" {
  count         = local.google_enabled ? 1 : 0
  user_pool_id  = aws_cognito_user_pool.this.id
  provider_name = "Google"
  provider_type = "Google"

  provider_details = {
    client_id                     = local.resolved_google_client_id
    client_secret                 = local.resolved_google_client_secret
    authorize_scopes              = "openid email profile"
    attributes_url                = "https://people.googleapis.com/v1/people/me?personFields="
    attributes_url_add_attributes = "true"
    authorize_url                 = "https://accounts.google.com/o/oauth2/v2/auth"
    oidc_issuer                   = "https://accounts.google.com"
    token_request_method          = "POST"
    token_url                     = "https://www.googleapis.com/oauth2/v4/token"
  }

  attribute_mapping = {
    email    = "email"
    username = "sub"
  }
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

# --- Pre Sign-Up Lambda (email domain restriction for federated users) ---

locals {
  domain_restriction_enabled = local.google_enabled && length(var.google_allowed_domains) > 0
}

data "archive_file" "pre_signup" {
  count       = local.domain_restriction_enabled ? 1 : 0
  type        = "zip"
  output_path = "${path.module}/.build/pre_signup.zip"

  source {
    content  = <<-PYTHON
import os, json

ALLOWED_DOMAINS = json.loads(os.environ.get("ALLOWED_DOMAINS", "[]"))

def handler(event, context):
    email = event["request"]["userAttributes"].get("email", "")
    if ALLOWED_DOMAINS:
        domain = email.split("@")[-1].lower() if "@" in email else ""
        if domain not in ALLOWED_DOMAINS:
            raise Exception(f"Email domain '{domain}' is not allowed.")
    return event
PYTHON
    filename = "index.py"
  }
}

resource "aws_lambda_function" "pre_signup" {
  count         = local.domain_restriction_enabled ? 1 : 0
  function_name = "${var.name}-pre-signup"
  role          = aws_iam_role.pre_signup[0].arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 5
  filename      = data.archive_file.pre_signup[0].output_path

  source_code_hash = data.archive_file.pre_signup[0].output_base64sha256

  environment {
    variables = {
      ALLOWED_DOMAINS = jsonencode([for d in var.google_allowed_domains : lower(d)])
    }
  }
}

resource "aws_iam_role" "pre_signup" {
  count = local.domain_restriction_enabled ? 1 : 0
  name  = "${var.name}-pre-signup"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "pre_signup_logs" {
  count      = local.domain_restriction_enabled ? 1 : 0
  role       = aws_iam_role.pre_signup[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_permission" "pre_signup" {
  count         = local.domain_restriction_enabled ? 1 : 0
  statement_id  = "AllowCognitoInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pre_signup[0].function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.this.arn
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
