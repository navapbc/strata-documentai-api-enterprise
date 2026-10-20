output "user_pool_id" {
  description = "ID of the Cognito user pool."
  value       = aws_cognito_user_pool.this.id
}

output "user_pool_arn" {
  description = "ARN of the Cognito user pool."
  value       = aws_cognito_user_pool.this.arn
}

output "client_id" {
  description = "ID of the Cognito user pool app client."
  value       = aws_cognito_user_pool_client.this.id
}

output "user_pool_domain" {
  description = "Cognito user pool domain for OAuth flows. Null if Google SSO is not configured."
  value       = local.google_enabled ? nonsensitive(aws_cognito_user_pool_domain.this[0].domain) : null
}

output "google_enabled" {
  description = "Whether Google SSO is configured."
  value       = nonsensitive(local.google_enabled)
}
