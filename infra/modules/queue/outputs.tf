output "queue_url" {
  description = "URL of the main SQS queue."
  value       = aws_sqs_queue.this.url
}

output "queue_arn" {
  description = "ARN of the main SQS queue."
  value       = aws_sqs_queue.this.arn
}

output "queue_name" {
  description = "Name of the main SQS queue."
  value       = aws_sqs_queue.this.name
}

output "dlq_url" {
  description = "URL of the dead-letter queue."
  value       = aws_sqs_queue.dlq.url
}

output "dlq_arn" {
  description = "ARN of the dead-letter queue."
  value       = aws_sqs_queue.dlq.arn
}

output "send_policy_arn" {
  description = "ARN of the IAM policy granting send access to the queue."
  value       = aws_iam_policy.send.arn
}

output "consume_policy_arn" {
  description = "ARN of the IAM policy granting receive/delete access to the queue."
  value       = aws_iam_policy.consume.arn
}
