variable "service_name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "image_repository_url" {
  type = string
}

variable "image_repository_arn" {
  type        = string
  description = "ECR repository ARN, used to scope the task executor's image-pull permissions"
}

variable "image_tag" {
  type = string
}

variable "container_port" {
  type    = number
  default = 8000
}

variable "cpu" {
  type    = number
  default = 256
}

variable "memory" {
  type    = number
  default = 512
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "environment_variables" {
  type    = map(string)
  default = {}
}

variable "extra_policy_arns" {
  type    = map(string)
  default = {}
}

variable "file_upload_jobs" {
  type = map(object({
    source_bucket = string
    path_prefix   = string
    task_command  = list(string)
  }))
  default = {}
}

variable "is_temporary" {
  type    = bool
  default = false
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  cluster_name   = var.service_name
  container_name = var.service_name
  log_group_name = "service/${var.service_name}"
  image_url      = "${var.image_repository_url}:${var.image_tag}"

  environment_variables = [
    for name, value in merge({
      PORT               = tostring(var.container_port)
      AWS_DEFAULT_REGION = data.aws_region.current.name
      AWS_REGION         = data.aws_region.current.name
      IMAGE_TAG          = var.image_tag
    }, var.environment_variables) :
    { name = name, value = value }
  ]
}

# --- ECS Cluster ---

resource "aws_ecs_cluster" "this" {
  name = local.cluster_name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# --- CloudWatch Logs ---

resource "aws_cloudwatch_log_group" "service" {
  name              = local.log_group_name
  retention_in_days = 30
}

# --- IAM ---

data "aws_iam_policy_document" "ecs_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "task_executor" {
  name               = "${var.service_name}-task-executor"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

resource "aws_iam_role" "task" {
  name               = "${var.service_name}-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

data "aws_iam_policy_document" "task_executor" {
  statement {
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogStreams",
    ]
    resources = ["${aws_cloudwatch_log_group.service.arn}:*"]
  }

  statement {
    # GetAuthorizationToken is an account-level action that does not support
    # resource scoping, so "*" is required by IAM here.
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = [var.image_repository_arn]
  }
}

resource "aws_iam_role_policy" "task_executor" {
  name   = "${var.service_name}-task-executor"
  role   = aws_iam_role.task_executor.id
  policy = data.aws_iam_policy_document.task_executor.json
}

resource "aws_iam_role_policy_attachment" "extra_policies" {
  for_each   = var.extra_policy_arns
  role       = aws_iam_role.task.name
  policy_arn = each.value
}

# --- Security Groups ---

# Public ingress (0.0.0.0/0) on 80/443 is intentional: this is a public-facing
# API. If the service should ever be internal-only, replace the CIDRs below with
# the allowed ranges. NOTE: this whole ECS/ALB path is currently dormant — the
# deployment runs the Lambda API (use_lambda_api = true), so module.service has
# count 0 and nothing here is provisioned today.
resource "aws_security_group" "alb" {
  name_prefix = "${var.service_name}-alb-"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group" "app" {
  name_prefix = "${var.service_name}-app-"
  vpc_id      = var.vpc_id

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_egress_rule" "app_egress" {
  security_group_id = aws_security_group.app.id
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_ingress_rule" "app_from_alb" {
  security_group_id            = aws_security_group.app.id
  from_port                    = var.container_port
  to_port                      = var.container_port
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.alb.id
}

# --- ALB ---

resource "aws_lb" "this" {
  name                       = var.service_name
  idle_timeout               = 120
  internal                   = false
  security_groups            = [aws_security_group.alb.id]
  subnets                    = var.public_subnet_ids
  drop_invalid_header_fields = true

  enable_deletion_protection = !var.is_temporary
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.this.arn
  }
}

resource "aws_lb_target_group" "this" {
  name_prefix          = "app-"
  port                 = var.container_port
  protocol             = "HTTP"
  vpc_id               = var.vpc_id
  target_type          = "ip"
  deregistration_delay = 30

  health_check {
    path                = "/health"
    port                = var.container_port
    healthy_threshold   = 2
    unhealthy_threshold = 10
    interval            = 30
    timeout             = 29
    matcher             = "200-299"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# --- ECS Task Definition ---

resource "aws_ecs_task_definition" "this" {
  family             = var.service_name
  execution_role_arn = aws_iam_role.task_executor.arn
  task_role_arn      = aws_iam_role.task.arn
  cpu                = var.cpu
  memory             = var.memory

  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"

  container_definitions = jsonencode([{
    name      = local.container_name
    image     = local.image_url
    cpu       = var.cpu
    memory    = var.memory
    essential = true

    portMappings = [{
      containerPort = var.container_port
      hostPort      = var.container_port
      protocol      = "tcp"
    }]

    environment = local.environment_variables

    healthCheck = {
      command  = ["CMD-SHELL", "wget --quiet --output-document=/dev/null http://127.0.0.1:${var.container_port}/health || exit 1"]
      interval = 30
      retries  = 3
      timeout  = 5
    }

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.service.name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = var.service_name
      }
    }

    linuxParameters = {
      capabilities = {
        add  = []
        drop = ["ALL"]
      }
      initProcessEnabled = true
    }
  }])
}

# --- ECS Service ---

resource "aws_ecs_service" "this" {
  name            = var.service_name
  cluster         = aws_ecs_cluster.this.arn
  launch_type     = "FARGATE"
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = var.desired_count

  network_configuration {
    assign_public_ip = false
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.app.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.this.arn
    container_name   = local.container_name
    container_port   = var.container_port
  }

  lifecycle {
    ignore_changes = [desired_count]
  }
}

# --- File Upload Jobs (S3 → EventBridge → Step Functions → ECS) ---

resource "aws_cloudwatch_event_rule" "file_upload" {
  for_each = var.file_upload_jobs

  name = "${var.service_name}-${each.key}"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = { name = [each.value.source_bucket] }
      object = { key = [{ prefix = each.value.path_prefix }] }
    }
  })
}

data "aws_iam_policy_document" "events_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "events" {
  name               = "${var.service_name}-events"
  assume_role_policy = data.aws_iam_policy_document.events_assume.json
}

data "aws_iam_policy_document" "sfn_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "sfn" {
  name               = "${var.service_name}-sfn"
  assume_role_policy = data.aws_iam_policy_document.sfn_assume.json
}

resource "aws_iam_role_policy" "sfn_ecs" {
  name = "${var.service_name}-sfn-ecs"
  role = aws_iam_role.sfn.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecs:RunTask",
          "ecs:StopTask",
          "ecs:DescribeTasks",
        ]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = [aws_iam_role.task_executor.arn, aws_iam_role.task.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["events:PutTargets", "events:PutRule", "events:DescribeRule"]
        Resource = "*"
      },
    ]
  })
}

resource "aws_iam_role_policy" "events_sfn" {
  name = "${var.service_name}-events-sfn"
  role = aws_iam_role.events.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["states:StartExecution"]
      Resource = [for k, v in aws_sfn_state_machine.file_upload : v.arn]
    }]
  })
}

resource "aws_sfn_state_machine" "file_upload" {
  for_each = var.file_upload_jobs

  name     = "${var.service_name}-${each.key}"
  role_arn = aws_iam_role.sfn.arn

  definition = jsonencode({
    StartAt = "RunTask"
    States = {
      RunTask = {
        Type     = "Task"
        Resource = "arn:aws:states:::ecs:runTask.sync"
        Parameters = {
          Cluster        = aws_ecs_cluster.this.arn
          TaskDefinition = aws_ecs_task_definition.this.arn
          LaunchType     = "FARGATE"
          NetworkConfiguration = {
            AwsvpcConfiguration = {
              Subnets        = var.private_subnet_ids
              SecurityGroups = [aws_security_group.app.id]
            }
          }
          Overrides = {
            ContainerOverrides = [{
              Name        = local.container_name
              "Command.$" = "$.task_command"
            }]
          }
        }
        End = true
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "file_upload" {
  for_each = var.file_upload_jobs

  target_id = "${var.service_name}-${each.key}"
  rule      = aws_cloudwatch_event_rule.file_upload[each.key].name
  arn       = aws_sfn_state_machine.file_upload[each.key].arn
  role_arn  = aws_iam_role.events.arn

  input_transformer {
    input_paths = {
      bucket_name = "$.detail.bucket.name"
      object_key  = "$.detail.object.key"
    }
    input_template = replace(replace(jsonencode({
      task_command = each.value.task_command
    }), "\\u003c", "<"), "\\u003e", ">")
  }
}

# --- Outputs ---

output "alb_dns_name" {
  value = aws_lb.this.dns_name
}

output "cluster_arn" {
  value = aws_ecs_cluster.this.arn
}

output "task_role_name" {
  value = aws_iam_role.task.name
}

# CloudWatch dimension identifiers for the monitoring module.
# ALB/target-group "full names" use the ARN suffix (e.g. app/<name>/<id>).
output "alb_arn_suffix" {
  value = aws_lb.this.arn_suffix
}

output "target_group_arn_suffix" {
  value = aws_lb_target_group.this.arn_suffix
}

output "cluster_name" {
  value = local.cluster_name
}

output "service_name" {
  value = aws_ecs_service.this.name
}
