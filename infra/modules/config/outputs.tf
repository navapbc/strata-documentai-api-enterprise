output "parameter_arns" {
  description = "Map of parameter name to its created SSM parameter ARN."
  value       = { for k, v in aws_ssm_parameter.this : k => v.arn }
}

output "read_policy_arn" {
  description = "ARN of the IAM policy granting read access to all parameters under the prefix."
  value       = aws_iam_policy.read.arn
}
