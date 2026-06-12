output "user_pool_id" {
  description = "ID of the Cognito user pool."
  value       = aws_cognito_user_pool.this.id
}

output "client_id" {
  description = "ID of the Cognito user pool app client."
  value       = aws_cognito_user_pool_client.this.id
}

output "access_policy_arn" {
  description = "ARN of the IAM policy granting access to the user pool."
  value       = aws_iam_policy.access.arn
}
