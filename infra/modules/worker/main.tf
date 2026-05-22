# Lambda worker module
# S3 event → EventBridge → SQS → Lambda (with DLQ)

variable "function_name" {
  type = string
}

variable "image_uri" {
  type = string
}

variable "command" {
  type        = list(string)
  description = "CMD override for the container (Lambda handler entrypoint)"
}

variable "timeout" {
  type    = number
  default = 300
}

variable "memory_size" {
  type    = number
  default = 512
}

variable "environment_variables" {
  type    = map(string)
  default = {}
}

variable "policy_arns" {
  type        = map(string)
  description = "IAM policy ARNs to attach to the Lambda execution role"
  default     = {}
}

variable "sqs_trigger" {
  type = object({
    source_bucket = string
    path_prefix   = string
  })
  description = "S3 event trigger config routed through SQS"
  default     = null
}

variable "schedule_expression" {
  type        = string
  description = "EventBridge schedule expression (e.g. rate(1 day))"
  default     = null
}

variable "vpc_config" {
  type = object({
    subnet_ids         = list(string)
    security_group_ids = list(string)
  })
  default = null
}

data "aws_region" "current" {}

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

# SQS permissions for Lambda
resource "aws_iam_role_policy" "sqs_access" {
  count = var.sqs_trigger != null ? 1 : 0
  name  = "${var.function_name}-sqs"
  role  = aws_iam_role.this.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
      ]
      Resource = [aws_sqs_queue.this[0].arn]
    }]
  })
}

# --- Lambda Function ---

resource "aws_lambda_function" "this" {
  function_name = var.function_name
  role          = aws_iam_role.this.arn
  package_type  = "Image"
  image_uri     = var.image_uri
  timeout       = var.timeout
  memory_size   = var.memory_size

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

# --- SQS Queue + DLQ (for S3 event triggers) ---

resource "aws_sqs_queue" "dlq" {
  count = var.sqs_trigger != null ? 1 : 0
  name  = "${var.function_name}-dlq"

  message_retention_seconds = 1209600 # 14 days
}

resource "aws_sqs_queue" "this" {
  count = var.sqs_trigger != null ? 1 : 0
  name  = "${var.function_name}-queue"

  visibility_timeout_seconds = var.timeout * 6
  message_retention_seconds  = 86400 # 1 day

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq[0].arn
    maxReceiveCount     = 3
  })
}

# SQS policy to allow EventBridge to send messages
resource "aws_sqs_queue_policy" "this" {
  count     = var.sqs_trigger != null ? 1 : 0
  queue_url = aws_sqs_queue.this[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.this[0].arn
    }]
  })
}

# Lambda SQS event source mapping
resource "aws_lambda_event_source_mapping" "sqs" {
  count            = var.sqs_trigger != null ? 1 : 0
  event_source_arn = aws_sqs_queue.this[0].arn
  function_name    = aws_lambda_function.this.arn
  batch_size       = 1
}

# --- EventBridge Rule (S3 → SQS) ---

resource "aws_cloudwatch_event_rule" "s3_trigger" {
  count = var.sqs_trigger != null ? 1 : 0
  name  = "${var.function_name}-s3-trigger"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = { name = [var.sqs_trigger.source_bucket] }
      object = { key = [{ prefix = var.sqs_trigger.path_prefix }] }
    }
  })
}

resource "aws_cloudwatch_event_target" "sqs" {
  count     = var.sqs_trigger != null ? 1 : 0
  rule      = aws_cloudwatch_event_rule.s3_trigger[0].name
  target_id = var.function_name
  arn       = aws_sqs_queue.this[0].arn
}

# --- EventBridge Schedule (for scheduled jobs) ---

resource "aws_cloudwatch_event_rule" "schedule" {
  count               = var.schedule_expression != null ? 1 : 0
  name                = "${var.function_name}-schedule"
  schedule_expression = var.schedule_expression
}

resource "aws_cloudwatch_event_target" "schedule" {
  count     = var.schedule_expression != null ? 1 : 0
  rule      = aws_cloudwatch_event_rule.schedule[0].name
  target_id = var.function_name
  arn       = aws_lambda_function.this.arn
}

resource "aws_lambda_permission" "schedule" {
  count         = var.schedule_expression != null ? 1 : 0
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule[0].arn
}

# --- Outputs ---

output "function_name" {
  value = aws_lambda_function.this.function_name
}

output "function_arn" {
  value = aws_lambda_function.this.arn
}

output "role_arn" {
  value = aws_iam_role.this.arn
}

output "queue_url" {
  value = var.sqs_trigger != null ? aws_sqs_queue.this[0].url : null
}
