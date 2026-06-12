output "sns_topic_arn" {
  description = "ARN of the SNS topic that alarm notifications are published to."
  value       = aws_sns_topic.alarms.arn
}
