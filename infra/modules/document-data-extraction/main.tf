locals {
  bda_tags = [
    for key, value in var.tags : {
      key   = key
      value = value
    }
  ]

  blueprint_arns = [
    for bp in var.blueprints : bp
    if startswith(bp, "arn:")
  ]

  blueprint_files = [
    for bp in var.blueprints : bp
    if !startswith(bp, "arn:")
  ]

  custom_blueprints_map = {
    for file_path in local.blueprint_files :
    replace(basename(file_path), ".json", "") => {
      schema = file(file_path)
      type   = "DOCUMENT"
    }
  }

  all_blueprints = concat(
    [for k, v in awscc_bedrock_blueprint.this : {
      blueprint_arn   = v.blueprint_arn
      blueprint_stage = v.blueprint_stage
    }],
    [for arn in local.blueprint_arns : {
      blueprint_arn   = arn
      blueprint_stage = "LIVE"
    }]
  )
}

resource "awscc_bedrock_data_automation_project" "this" {
  project_name                  = "${var.name}-project"
  project_description           = "BDA project for ${var.name}"
  tags                          = local.bda_tags
  standard_output_configuration = var.standard_output_configuration

  custom_output_configuration = length(local.all_blueprints) > 0 ? {
    blueprints = local.all_blueprints
  } : null
}

resource "awscc_bedrock_blueprint" "this" {
  for_each = local.custom_blueprints_map

  blueprint_name = "${var.name}-${each.key}"
  schema         = each.value.schema
  type           = each.value.type
  tags           = local.bda_tags

  lifecycle {
    create_before_destroy = true
  }
}

# IAM policy for Bedrock access
data "aws_iam_policy_document" "access" {
  statement {
    actions = [
      "bedrock:InvokeDataAutomationAsync",
      "bedrock:GetDataAutomationProject",
      "bedrock:GetBlueprint",
      "bedrock:StartDataAutomationJob",
      "bedrock:GetDataAutomationJob",
      "bedrock:ListDataAutomationJobs",
    ]
    resources = [
      awscc_bedrock_data_automation_project.this.project_arn,
      "${awscc_bedrock_data_automation_project.this.project_arn}/*",
      "arn:aws:bedrock:*:*:blueprint/*",
      "arn:aws:bedrock:*:*:data-automation-profile/*",
    ]
  }
}

resource "aws_iam_policy" "access" {
  name   = "${var.name}-bedrock-access"
  policy = data.aws_iam_policy_document.access.json
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}
