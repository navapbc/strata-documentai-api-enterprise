# Lambda worker module
# S3 event → EventBridge → Lambda (with DLQ on EventBridge rule)

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

variable "s3_trigger" {
  type = object({
    source_bucket = string
    path_prefix   = string
  })
  description = "S3 event trigger config routed through EventBridge"
  default     = null
}

variable "sqs_trigger" {
  type = object({
    queue_arn                   = string
    batch_size                  = optional(number, 10)
    max_batching_window_seconds = optional(number, 300)
  })
  description = "SQS queue trigger config"
  default     = null
}

variable "schedules" {
  type = list(object({
    name                = string
    schedule_expression = string
    input               = optional(map(string))
  }))
  description = "Multiple EventBridge schedules with optional input payloads"
  default     = []
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
      Resource = [var.sqs_trigger.queue_arn]
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

# --- DLQ for failed EventBridge invocations ---

resource "aws_sqs_queue" "dlq" {
  count = var.s3_trigger != null ? 1 : 0
  name  = "${var.function_name}-dlq"

  message_retention_seconds = 1209600 # 14 days
}

# --- EventBridge Rule (S3 → Lambda) ---

resource "aws_cloudwatch_event_rule" "s3_trigger" {
  count = var.s3_trigger != null ? 1 : 0
  name  = "${var.function_name}-s3-trigger"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = { name = [var.s3_trigger.source_bucket] }
      object = { key = [{ prefix = var.s3_trigger.path_prefix }] }
    }
  })
}

resource "aws_cloudwatch_event_target" "lambda" {
  count     = var.s3_trigger != null ? 1 : 0
  rule      = aws_cloudwatch_event_rule.s3_trigger[0].name
  target_id = var.function_name
  arn       = aws_lambda_function.this.arn

  dead_letter_config {
    arn = aws_sqs_queue.dlq[0].arn
  }

  retry_policy {
    maximum_event_age_in_seconds = 3600
    maximum_retry_attempts       = 3
  }
}

resource "aws_lambda_permission" "eventbridge_s3" {
  count         = var.s3_trigger != null ? 1 : 0
  statement_id  = "AllowEventBridgeS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.s3_trigger[0].arn
}

# --- SQS Event Source Mapping ---

resource "aws_lambda_event_source_mapping" "sqs" {
  count                              = var.sqs_trigger != null ? 1 : 0
  event_source_arn                   = var.sqs_trigger.queue_arn
  function_name                      = aws_lambda_function.this.arn
  batch_size                         = var.sqs_trigger.batch_size
  maximum_batching_window_in_seconds = var.sqs_trigger.max_batching_window_seconds
}

# --- EventBridge Schedules (with optional input payloads) ---

resource "aws_cloudwatch_event_rule" "schedules" {
  for_each            = { for s in var.schedules : s.name => s }
  name                = "${var.function_name}-${each.key}"
  schedule_expression = each.value.schedule_expression
}

resource "aws_cloudwatch_event_target" "schedules" {
  for_each  = { for s in var.schedules : s.name => s }
  rule      = aws_cloudwatch_event_rule.schedules[each.key].name
  target_id = "${var.function_name}-${each.key}"
  arn       = aws_lambda_function.this.arn
  input     = each.value.input != null ? jsonencode(each.value.input) : null
}

resource "aws_lambda_permission" "schedules" {
  for_each      = { for s in var.schedules : s.name => s }
  statement_id  = "AllowEventBridge-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedules[each.key].arn
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

# DLQ identifiers for monitoring. Null when this worker has no S3 trigger
# (only s3_trigger workers create a DLQ).
output "dlq_arn" {
  value = var.s3_trigger != null ? aws_sqs_queue.dlq[0].arn : null
}

output "dlq_name" {
  value = var.s3_trigger != null ? aws_sqs_queue.dlq[0].name : null
}
