variable "secrets" {
  type = map(object({
    manage_method     = string # "generated" or "manual"
    secret_store_name = string
  }))
  description = "Map of secret configurations"

  validation {
    condition     = alltrue([for s in values(var.secrets) : contains(["manual", "generated"], s.manage_method)])
    error_message = "manage_method must be 'manual' or 'generated'"
  }
}

locals {
  generated_secrets = {
    for name, config in var.secrets :
    name => config if config.manage_method == "generated"
  }
  manual_secrets = {
    for name, config in var.secrets :
    name => config if config.manage_method == "manual"
  }
}

resource "random_password" "this" {
  for_each = local.generated_secrets

  length           = 64
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "aws_ssm_parameter" "generated" {
  for_each = local.generated_secrets

  name  = each.value.secret_store_name
  type  = "SecureString"
  value = random_password.this[each.key].result
}

data "aws_ssm_parameter" "manual" {
  for_each = local.manual_secrets
  name     = each.value.secret_store_name
}

output "secret_arns" {
  value = merge(
    { for k, v in aws_ssm_parameter.generated : k => v.arn },
    { for k, v in data.aws_ssm_parameter.manual : k => v.arn },
  )
}
