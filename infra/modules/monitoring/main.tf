# Monitoring module: SNS topic + alarms + a CloudWatch dashboard.
#
# Dashboard layout is ported from the CDK reference
# (idp-platform-copa-v2/lib/stacks/cloudwatch-dashboard-stack.ts), sourcing
# identifiers from module outputs instead of SSM lookups.
#
# Alarms are gated by var.create_alarms (prd only); the dashboard by
# var.create_dashboard (all envs). The SNS topic is always created so whoever
# has prod access can attach subscriptions later via tfvars without a code change.

locals {
  period = 300

  # alarm_workers: map of function_name -> timeout_ms, used by for_each on alarm resources.
  alarm_workers = {
    for k, w in var.workers : w.function_name => w.timeout_seconds * 1000 * 0.8
  }

  dlq_names = compact([
    var.document_processor_dlq_name,
    var.bda_output_dlq_name,
    var.metrics_queue_dlq_name,
  ])

  alarm_worker_names = var.create_alarms ? local.alarm_workers : {}
  alarm_dlq_names    = var.create_alarms ? toset(local.dlq_names) : toset([])
  # alarm_scheduled_workers: map of function_name -> invocation_window_seconds for scheduled workers.
  alarm_scheduled_workers = var.create_alarms ? { for k, w in var.workers : w.function_name => w.invocation_window_seconds if w.scheduled } : {}
}

# --- SNS topic + subscriptions ---

resource "aws_sns_topic" "alarms" {
  name = "${var.name_prefix}-alarms"
}

resource "aws_sns_topic_subscription" "email" {
  for_each  = toset(var.alarm_emails)
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = each.value
}

# --- Optional AWS Chatbot → Slack ---

data "aws_iam_policy_document" "chatbot_assume" {
  count = var.slack != null ? 1 : 0
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["chatbot.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "chatbot" {
  count              = var.slack != null ? 1 : 0
  name               = "${var.name_prefix}-chatbot"
  assume_role_policy = data.aws_iam_policy_document.chatbot_assume[0].json
}

resource "aws_iam_role_policy_attachment" "chatbot_readonly" {
  count      = var.slack != null ? 1 : 0
  role       = aws_iam_role.chatbot[0].name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchReadOnlyAccess"
}

resource "aws_chatbot_slack_channel_configuration" "this" {
  count              = var.slack != null ? 1 : 0
  configuration_name = "${var.name_prefix}-slack"
  iam_role_arn       = aws_iam_role.chatbot[0].arn
  slack_channel_id   = var.slack.channel_id
  slack_team_id      = var.slack.workspace_id
  sns_topic_arns     = [aws_sns_topic.alarms.arn]
}
