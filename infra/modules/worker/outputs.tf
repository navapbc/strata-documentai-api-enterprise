output "function_name" {
  description = "Name of the worker Lambda function."
  value       = aws_lambda_function.this.function_name
}

output "function_arn" {
  description = "ARN of the worker Lambda function."
  value       = aws_lambda_function.this.arn
}

output "role_arn" {
  description = "ARN of the worker's Lambda execution role."
  value       = aws_iam_role.this.arn
}

# DLQ identifiers for monitoring. Null when this worker has no S3 trigger
# (only s3_trigger workers create a DLQ).
output "dlq_arn" {
  description = "ARN of the worker's dead-letter queue, or null when there is no S3 trigger."
  value       = var.s3_trigger != null ? aws_sqs_queue.dlq[0].arn : null
}

output "dlq_name" {
  description = "Name of the worker's dead-letter queue, or null when there is no S3 trigger."
  value       = var.s3_trigger != null ? aws_sqs_queue.dlq[0].name : null
}
