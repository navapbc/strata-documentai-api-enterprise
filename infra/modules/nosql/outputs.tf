output "table_name" {
  description = "Name of the DynamoDB table."
  value       = aws_dynamodb_table.this.name
}

output "table_arn" {
  description = "ARN of the DynamoDB table."
  value       = aws_dynamodb_table.this.arn
}

output "access_policy_arn" {
  description = "ARN of the IAM policy granting read/write access to the table and its indexes."
  value       = aws_iam_policy.access.arn
}

output "kms_key_arn" {
  description = "ARN of the KMS key used to encrypt the table."
  value       = aws_kms_key.this.arn
}
