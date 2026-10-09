# AWS-managed key ARNs for SSE-KMS access (buckets use aws/s3, SecureString
# params use aws/ssm), resolved so the ddb policies can scope to them.
data "aws_kms_alias" "s3" {
  name = "alias/aws/s3"
}

data "aws_kms_alias" "ssm" {
  name = "alias/aws/ssm"
}

locals {
  # All DynamoDB table + index ARNs, shared across both ddb policies.
  ddb_table_arns = [
    "${module.document_metadata.table_arn}",
    "${module.document_metadata.table_arn}/index/*",
    "${module.api_keys.table_arn}",
    "${module.api_keys.table_arn}/index/*",
    "${module.tenants.table_arn}",
    "${module.tenants.table_arn}/index/*",
    "${module.tenant_request_counts.table_arn}",
    "${module.tenant_request_counts.table_arn}/index/*",
    "${module.extraction_rules.table_arn}",
    "${module.extraction_rules.table_arn}/index/*",
    "${module.document_categories.table_arn}",
    "${module.document_categories.table_arn}/index/*",
    "${module.document_batches.table_arn}",
    "${module.document_batches.table_arn}/index/*",
    "${module.document_builds.table_arn}",
    "${module.document_builds.table_arn}/index/*",
    "${module.audit_events.table_arn}",
    "${module.audit_events.table_arn}/index/*",
  ]

  # KMS keys required for DDB + S3 + SSM access, shared across both ddb policies.
  ddb_kms_key_arns = concat(
    [for m in [
      module.document_metadata, module.api_keys, module.tenants,
      module.tenant_request_counts, module.extraction_rules, module.document_categories,
      module.document_batches, module.document_builds, module.audit_events,
    ] : m.kms_key_arn],
    [
      data.aws_kms_alias.s3.target_key_arn,
      data.aws_kms_alias.ssm.target_key_arn,
    ],
  )
}

# --- DynamoDB ---

# Shared by API Lambda and all workers.
data "aws_iam_policy_document" "ddb_access" {
  statement {
    actions = [
      "dynamodb:BatchWriteItem",
      "dynamodb:DeleteItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:BatchGetItem",
      "dynamodb:GetItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:DescribeTable",
    ]
    resources = local.ddb_table_arns
  }

  statement {
    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
      "kms:GenerateDataKey",
    ]
    resources = local.ddb_kms_key_arns
  }
}

resource "aws_iam_policy" "ddb_access" {
  name   = "${local.service_name}-ddb-access"
  policy = data.aws_iam_policy_document.ddb_access.json
}

# --- S3 ---

# API Lambda: input + output buckets (full access) + metrics bucket (read-only).
# No Athena results bucket — only workers query Athena.
data "aws_iam_policy_document" "s3_api" {
  statement {
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]
    resources = [
      module.input_bucket.bucket_arn,
      "${module.input_bucket.bucket_arn}/*",
      module.output_bucket.bucket_arn,
      "${module.output_bucket.bucket_arn}/*",
    ]
  }

  statement {
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
    ]
    resources = [
      module.metrics_bucket.bucket_arn,
      "${module.metrics_bucket.bucket_arn}/*",
    ]
  }
}

resource "aws_iam_policy" "s3_api" {
  name   = "${local.service_name}-s3-api"
  policy = data.aws_iam_policy_document.s3_api.json
}

# Workers: all four buckets — document-processor deletes originals,
# metrics workers write/read metrics + Athena results.
data "aws_iam_policy_document" "s3_worker" {
  statement {
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]
    resources = [
      module.input_bucket.bucket_arn,
      "${module.input_bucket.bucket_arn}/*",
      module.output_bucket.bucket_arn,
      "${module.output_bucket.bucket_arn}/*",
      module.metrics_bucket.bucket_arn,
      "${module.metrics_bucket.bucket_arn}/*",
      module.analytics.results_bucket_arn,
      "${module.analytics.results_bucket_arn}/*",
    ]
  }
}

resource "aws_iam_policy" "s3_worker" {
  name   = "${local.service_name}-s3-worker"
  policy = data.aws_iam_policy_document.s3_worker.json
}

# --- Bedrock + Textract ---

# API Lambda: GetDataAutomationStatus only (blueprint_test router).
# InvokeModel/Converse are worker-only — preclassification, bbox, and blur
# are all called from upsert_initial_ddb_record, which only document_processor invokes.
data "aws_iam_policy_document" "bedrock_api" {
  statement {
    actions = ["bedrock:GetDataAutomationStatus"]
    resources = [
      "arn:aws:bedrock:*:${local.account_id}:data-automation-invocation/*",
    ]
  }
}

resource "aws_iam_policy" "bedrock_api" {
  name   = "${local.service_name}-bedrock-api"
  policy = data.aws_iam_policy_document.bedrock_api.json
}

# Workers: full BDA invoke + job management + Converse + Textract.
data "aws_iam_policy_document" "bedrock_worker" {
  statement {
    actions = [
      "bedrock:InvokeDataAutomationAsync",
      "bedrock:GetDataAutomationProject",
      "bedrock:GetDataAutomationStatus",
      "bedrock:GetBlueprint",
      "bedrock:StartDataAutomationJob",
      "bedrock:GetDataAutomationJob",
      "bedrock:ListDataAutomationJobs",
    ]
    resources = [
      "arn:aws:bedrock:*:${local.account_id}:data-automation-project/*",
      "arn:aws:bedrock:*:${local.account_id}:data-automation-invocation/*",
      "arn:aws:bedrock:*:*:blueprint/*",
      "arn:aws:bedrock:*:*:data-automation-profile/*",
    ]
  }

  statement {
    actions = [
      "bedrock:InvokeModel",
      "bedrock:Converse",
    ]
    resources = [
      "arn:aws:bedrock:${var.region}:*:inference-profile/*",
      "arn:aws:bedrock:*::foundation-model/*",
    ]
  }

  statement {
    actions = [
      "textract:AnalyzeID",
      "textract:DetectDocumentText",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "bedrock_worker" {
  name   = "${local.service_name}-bedrock-worker"
  policy = data.aws_iam_policy_document.bedrock_worker.json
}

# --- Cognito ---

# API Lambda only — workers have no user-management paths.
# AdminGetUser, AdminCreateUser, AdminSetUserPassword, AdminInitiateAuth
# are not called anywhere in src — omitted intentionally.
data "aws_iam_policy_document" "cognito_user_mgmt" {
  statement {
    actions = [
      "cognito-idp:ListUsers",
      "cognito-idp:ListUsersInGroup",
      "cognito-idp:AdminListGroupsForUser",
      "cognito-idp:AdminAddUserToGroup",
      "cognito-idp:AdminRemoveUserFromGroup",
      "cognito-idp:AdminUpdateUserAttributes",
      "cognito-idp:AdminDeleteUserAttributes",
      "cognito-idp:AdminDeleteUser",
    ]
    resources = [module.identity_provider.user_pool_arn]
  }
}

resource "aws_iam_policy" "cognito_user_mgmt" {
  name   = "${local.service_name}-cognito-user-mgmt"
  policy = data.aws_iam_policy_document.cognito_user_mgmt.json
}

# --- Operational services (SSM + SQS + CloudWatch) ---

# API Lambda: SSM read + SQS send-only + CloudWatch.
# No SQS receive/delete (the API only enqueues metrics events, never polls).
data "aws_iam_policy_document" "pipeline_api" {
  statement {
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]
  }

  statement {
    actions   = ["sqs:SendMessage"]
    resources = [module.metrics_queue.queue_arn]
  }

  statement {
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:GetParametersByPath",
    ]
    resources = ["arn:aws:ssm:${var.region}:${local.account_id}:parameter${local.ssm_prefix}/*"]
  }
}

resource "aws_iam_policy" "pipeline_api" {
  name   = "${local.service_name}-pipeline-api"
  policy = data.aws_iam_policy_document.pipeline_api.json
}

# Workers: SSM read + SQS full + CloudWatch + Athena + Glue. No Cognito.
data "aws_iam_policy_document" "pipeline_worker" {
  statement {
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]
  }

  statement {
    actions = [
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
    ]
    resources = [module.metrics_queue.queue_arn]
  }

  statement {
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:GetParametersByPath",
    ]
    resources = ["arn:aws:ssm:${var.region}:${local.account_id}:parameter${local.ssm_prefix}/*"]
  }

  statement {
    actions = [
      "athena:StartQueryExecution",
      "athena:GetQueryExecution",
      "athena:GetQueryResults",
      "athena:StopQueryExecution",
    ]
    resources = ["arn:aws:athena:${var.region}:${local.account_id}:workgroup/${local.service_name}-analytics"]
  }

  statement {
    actions = [
      "glue:GetTable",
      "glue:GetDatabase",
      "glue:GetPartitions",
    ]
    resources = [
      "arn:aws:glue:${var.region}:${local.account_id}:catalog",
      "arn:aws:glue:${var.region}:${local.account_id}:database/*",
      "arn:aws:glue:${var.region}:${local.account_id}:table/*/*",
    ]
  }
}

resource "aws_iam_policy" "pipeline_worker" {
  name   = "${local.service_name}-pipeline-worker"
  policy = data.aws_iam_policy_document.pipeline_worker.json
}
