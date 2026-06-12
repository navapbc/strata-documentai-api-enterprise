output "secret_arns" {
  description = "Map of secret name to its SSM parameter ARN, covering both generated and manually-managed secrets."
  value = merge(
    { for k, v in aws_ssm_parameter.generated : k => v.arn },
    { for k, v in data.aws_ssm_parameter.manual : k => v.arn },
  )
}
