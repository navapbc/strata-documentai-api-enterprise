variable "parameters" {
  type        = map(string)
  description = "Map of parameter name to value"
  default     = {}
}

variable "prefix" {
  type        = string
  description = "SSM parameter path prefix (e.g. /docai/dev)"
}

resource "aws_ssm_parameter" "this" {
  for_each = var.parameters

  name  = "${var.prefix}/${each.key}"
  type  = "String"
  value = each.value
}

# IAM policy to read all parameters under the prefix
data "aws_iam_policy_document" "read" {
  statement {
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:GetParametersByPath",
    ]
    resources = ["arn:aws:ssm:*:*:parameter${var.prefix}/*"]
  }
}

resource "aws_iam_policy" "read" {
  name   = replace("${var.prefix}-ssm-read", "/", "-")
  policy = data.aws_iam_policy_document.read.json
}

output "parameter_arns" {
  value = { for k, v in aws_ssm_parameter.this : k => v.arn }
}

output "read_policy_arn" {
  value = aws_iam_policy.read.arn
}
