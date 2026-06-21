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

variable "bda_projects" {
  type = map(object({
    managed_blueprint_arns = list(string)
  }))
  description = "Map of BDA projects by preclassification category, each with its own managed blueprint ARNs"
  default = {
    tax_documents = {
      managed_blueprint_arns = [
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-w2-form",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-form-1040",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-form-1099-int",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-form-1099-misc",
      ]
    }
    employment_wages = {
      managed_blueprint_arns = [
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-payslip",
      ]
    }
    independent_earnings = {
      managed_blueprint_arns = [
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-invoice",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-form-1040-schedule-c",
      ]
    }
    government_benefits = {
      managed_blueprint_arns = []
    }
    private_benefits_and_settlements = {
      managed_blueprint_arns = [
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-workers-compensation-form",
      ]
    }
    court_ordered_benefits = {
      managed_blueprint_arns = []
    }
    financial_assets = {
      managed_blueprint_arns = [
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-bank-statement",
      ]
    }
    receipts_and_invoices = {
      managed_blueprint_arns = [
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-invoice",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-receipt",
      ]
    }
    recurring_bills = {
      managed_blueprint_arns = []
    }
    housing_expenses = {
      managed_blueprint_arns = []
    }
    debt_obligations = {
      managed_blueprint_arns = []
    }
    identity_verification = {
      managed_blueprint_arns = [
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-us-driver-license",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-us-passport",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-birth-certificate",
      ]
    }
    right_to_work = {
      managed_blueprint_arns = []
    }
    # Note: BDA has a limit of 40 blueprints per project (as of 2025).
    # The "all" project combines every managed and custom blueprint.
    # Monitor total count if adding more custom blueprints.
    all = {
      managed_blueprint_arns = [
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-w2-form",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-form-1040",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-form-1099-int",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-form-1099-misc",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-payslip",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-invoice",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-receipt",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-bank-statement",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-us-driver-license",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-us-passport",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-birth-certificate",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-workers-compensation-form",
        "arn:aws:bedrock:us-east-1:aws:blueprint/bedrock-data-automation-public-form-1040-schedule-c",
      ]
    }
  }
}
