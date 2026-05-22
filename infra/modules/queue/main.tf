variable "name" {
  type = string
}

variable "visibility_timeout_seconds" {
  type    = number
  default = 300
}

variable "message_retention_seconds" {
  type    = number
  default = 86400 # 1 day
}

variable "max_receive_count" {
  type    = number
  default = 3
}

variable "dlq_retention_seconds" {
  type    = number
  default = 1209600 # 14 days
}

# --- DLQ ---

resource "aws_sqs_queue" "dlq" {
  name                      = "${var.name}-dlq"
  message_retention_seconds = var.dlq_retention_seconds

  sqs_managed_sse_enabled = true
}

# --- Main Queue ---

resource "aws_sqs_queue" "this" {
  name                       = var.name
  visibility_timeout_seconds = var.visibility_timeout_seconds
  message_retention_seconds  = var.message_retention_seconds

  sqs_managed_sse_enabled = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.max_receive_count
  })
}

# --- IAM: send messages ---

data "aws_iam_policy_document" "send" {
  statement {
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.this.arn]
  }
}

resource "aws_iam_policy" "send" {
  name   = "${var.name}-send"
  policy = data.aws_iam_policy_document.send.json
}

# --- IAM: receive/consume messages ---

data "aws_iam_policy_document" "consume" {
  statement {
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
    ]
    resources = [aws_sqs_queue.this.arn]
  }
}

resource "aws_iam_policy" "consume" {
  name   = "${var.name}-consume"
  policy = data.aws_iam_policy_document.consume.json
}

# --- Outputs ---

output "queue_url" {
  value = aws_sqs_queue.this.url
}

output "queue_arn" {
  value = aws_sqs_queue.this.arn
}

output "queue_name" {
  value = aws_sqs_queue.this.name
}

output "dlq_url" {
  value = aws_sqs_queue.dlq.url
}

output "dlq_arn" {
  value = aws_sqs_queue.dlq.arn
}

output "send_policy_arn" {
  value = aws_iam_policy.send.arn
}

output "consume_policy_arn" {
  value = aws_iam_policy.consume.arn
}
