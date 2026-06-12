output "api_endpoint" {
  description = "Base invoke URL of the HTTP API."
  value       = aws_apigatewayv2_api.this.api_endpoint
}

output "api_id" {
  description = "ID of the HTTP API (ApiId dimension for CloudWatch metrics)."
  value       = aws_apigatewayv2_api.this.id
}

output "api_log_metrics" {
  description = "Custom metrics parsed from the access log, splitting document submissions from status-poll GETs."
  value = {
    namespace        = local.api_log_metric_namespace
    submitted_metric = aws_cloudwatch_log_metric_filter.documents_submitted.metric_transformation[0].name
    polls_metric     = aws_cloudwatch_log_metric_filter.document_status_polls.metric_transformation[0].name
  }
}

output "function_name" {
  description = "Name of the Lambda function backing the API."
  value       = aws_lambda_function.this.function_name
}

output "function_arn" {
  description = "ARN of the Lambda function backing the API."
  value       = aws_lambda_function.this.arn
}
