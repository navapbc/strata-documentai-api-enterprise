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
