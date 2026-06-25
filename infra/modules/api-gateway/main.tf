# --- IAM ---

data "aws_iam_policy_document" "assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "this" {
  name               = "${var.function_name}-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "vpc_access" {
  count      = var.vpc_config != null ? 1 : 0
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy_attachment" "extra" {
  for_each   = var.policy_arns
  role       = aws_iam_role.this.name
  policy_arn = each.value
}

# --- Lambda Function ---

resource "aws_lambda_function" "this" {
  function_name = var.function_name
  role          = aws_iam_role.this.arn
  package_type  = "Image"
  image_uri     = var.image_uri
  timeout       = var.timeout
  memory_size   = var.memory_size
  tags          = var.tags

  image_config {
    command = var.command
  }

  environment {
    variables = var.environment_variables
  }

  dynamic "vpc_config" {
    for_each = var.vpc_config != null ? [1] : []
    content {
      subnet_ids         = var.vpc_config.subnet_ids
      security_group_ids = var.vpc_config.security_group_ids
    }
  }
}

# --- API Gateway HTTP API ---
#
# NOTE (WAF): AWS WAF (wafv2) cannot be attached to an HTTP API (apigatewayv2) -
# WAF only associates with REST APIs, ALB, CloudFront, AppSync and Cognito. To
# put WAF in front of this API you'd need either a CloudFront distribution ahead
# of it (associate the web ACL there) or a migration to a REST API. Tracked as a
# follow-up rather than a code change here.

resource "aws_apigatewayv2_api" "this" {
  name          = var.function_name
  protocol_type = "HTTP"
  tags          = var.tags

  cors_configuration {
    allow_origins  = ["*"]
    allow_methods  = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    allow_headers  = ["Content-Type", "Authorization", "API-Key", "X-Trace-ID"]
    expose_headers = ["X-Trace-ID"]
    max_age        = 3600
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = "$default"
  auto_deploy = true
  tags        = var.tags

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      method         = "$context.httpMethod"
      path           = "$context.path"
      status         = "$context.status"
      responseLength = "$context.responseLength"
      latency        = "$context.integrationLatency"
    })
  }
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/apigateway/${var.function_name}"
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.this.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds   = 30000
}

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*"
}

# --- Access-log metric filters: split real submissions from status-poll traffic ---
#
# The API is a single $default route, so API Gateway's per-route Count can't tell a
# document submission apart from the status polling GETs that follow each submission.
# These filters parse the JSON access log (which carries method and path) into 
# dimensionless custom metrics for cloudwatch alarms and dashboards. Note that these 
# are "metric filters", not "logs-based metrics"

locals {
  api_log_metric_namespace = "DocumentAI/Api"
}

resource "aws_cloudwatch_log_metric_filter" "documents_submitted" {
  name           = "${var.function_name}-documents-submitted"
  log_group_name = aws_cloudwatch_log_group.api.name
  pattern        = "{ ($.method = \"POST\") && ($.path = \"/v1/documents\") }"

  metric_transformation {
    name          = "DocumentsSubmitted"
    namespace     = local.api_log_metric_namespace
    value         = "1"
    default_value = "0"
    unit          = "Count"
  }
}

resource "aws_cloudwatch_log_metric_filter" "document_status_polls" {
  name           = "${var.function_name}-document-status-polls"
  log_group_name = aws_cloudwatch_log_group.api.name
  pattern        = "{ ($.method = \"GET\") && ($.path = \"/v1/documents/*\") }"

  metric_transformation {
    name          = "DocumentStatusPolls"
    namespace     = local.api_log_metric_namespace
    value         = "1"
    default_value = "0"
    unit          = "Count"
  }
}
