# AWS-managed key ARNs for SSE-KMS access (buckets use aws/s3, SecureString
# params use aws/ssm), resolved so the ddb policies can scope to them.
data "aws_kms_alias" "s3" {
  name = "alias/aws/s3"
}

data "aws_kms_alias" "ssm" {
  name = "alias/aws/ssm"
}

locals {
  # All DynamoDB table and index ARNs, shared across both ddb policies.
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

  # KMS keys required for DDB, S3, SSM access, shared across both ddb policies.
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

# API Lambda: full write access, but DeleteItem only on tables that have delete routes.
# Tables with delete routes: api_keys (key rotation), document_builds (build page deletion),
# extraction_rules, document_categories. No delete routes exist for: document_metadata,
# tenant_request_counts, document_batches, tenants, audit_events.
data "aws_iam_policy_document" "ddb_access_api" {
  statement {
    actions = [
      "dynamodb:BatchWriteItem",
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
    actions = ["dynamodb:DeleteItem"]
    resources = [
      module.api_keys.table_arn,
      module.document_builds.table_arn,
      module.extraction_rules.table_arn,
      module.document_categories.table_arn,
    ]
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

resource "aws_iam_policy" "ddb_access_api" {
  name   = "${local.service_name}-ddb-access-api"
  policy = data.aws_iam_policy_document.ddb_access_api.json
}

# document-processor and bda-result-processor: no delete routes - DeleteItem omitted.
data "aws_iam_policy_document" "ddb_access_workers" {
  statement {
    actions = [
      "dynamodb:BatchWriteItem",
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

resource "aws_iam_policy" "ddb_access_workers" {
  name   = "${local.service_name}-ddb-access-workers"
  policy = data.aws_iam_policy_document.ddb_access_workers.json
}

# document-reaper: document_metadata table only (query stale records, update status).
data "aws_iam_policy_document" "ddb_reaper" {
  statement {
    actions = [
      "dynamodb:GetItem",
      "dynamodb:Query",
      "dynamodb:UpdateItem",
    ]
    resources = [
      module.document_metadata.table_arn,
      "${module.document_metadata.table_arn}/index/*",
      module.document_batches.table_arn,
      "${module.document_batches.table_arn}/index/*",
    ]
  }

  statement {
    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
      "kms:GenerateDataKey",
    ]
    resources = [
      module.document_metadata.kms_key_arn,
      module.document_batches.kms_key_arn,
    ]
  }
}

resource "aws_iam_policy" "ddb_reaper" {
  name   = "${local.service_name}-ddb-reaper"
  policy = data.aws_iam_policy_document.ddb_reaper.json
}

# --- S3 ---

# API Lambda: input and output buckets (full access), metrics bucket (read-only).
# No Athena results bucket - only workers query Athena.
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

# document-processor and bda-result-processor: input and output buckets (full access).
# document-processor deletes originals after processing; bda-result-processor reads output.
data "aws_iam_policy_document" "s3_document_read_write" {
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
}

resource "aws_iam_policy" "s3_document_read_write" {
  name   = "${local.service_name}-s3-worker"
  policy = data.aws_iam_policy_document.s3_document_read_write.json
}

# metrics-processor: write raw records to metrics bucket only.
data "aws_iam_policy_document" "s3_metrics_write" {
  statement {
    actions = [
      "s3:PutObject",
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]
    resources = [
      module.metrics_bucket.bucket_arn,
      "${module.metrics_bucket.bucket_arn}/*",
    ]
  }
}

resource "aws_iam_policy" "s3_metrics_write" {
  name   = "${local.service_name}-s3-metrics-write"
  policy = data.aws_iam_policy_document.s3_metrics_write.json
}

# metrics-aggregator and usage-report: metrics bucket (read,  write), Athena results bucket.
data "aws_iam_policy_document" "s3_metrics_read_write" {
  statement {
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]
    resources = [
      module.metrics_bucket.bucket_arn,
      "${module.metrics_bucket.bucket_arn}/*",
      module.analytics.results_bucket_arn,
      "${module.analytics.results_bucket_arn}/*",
    ]
  }
}

resource "aws_iam_policy" "s3_metrics_read_write" {
  name   = "${local.service_name}-s3-metrics-read-write"
  policy = data.aws_iam_policy_document.s3_metrics_read_write.json
}

# --- Bedrock and Textract ---

locals {
  bda_project_arns = [for k, v in module.bedrock_data_automation : v.project_arn]
}

# API Lambda: extraction_test_runner router calls InvokeDataAutomationAsync and
# GetDataAutomationStatus via the standard document pipeline (POST /v1/admin/extraction-test).
# InvokeModel/Converse are worker-only - preclassification, bbox, and blur
# are all called from upsert_initial_ddb_record, which only document_processor invokes.
data "aws_iam_policy_document" "bedrock_api" {
  statement {
    actions = [
      "bedrock:InvokeDataAutomationAsync",
      "bedrock:GetDataAutomationStatus",
    ]
    resources = concat(
      local.bda_project_arns,
      [
        "arn:aws:bedrock:*:${local.account_id}:data-automation-invocation/*",
        "arn:aws:bedrock:*:*:data-automation-profile/*",
      ],
    )
  }
}

resource "aws_iam_policy" "bedrock_api" {
  name   = "${local.service_name}-bedrock-api"
  policy = data.aws_iam_policy_document.bedrock_api.json
}

# document-processor: full BDA invoke, job management, Converse, Textract.
data "aws_iam_policy_document" "document_processor" {
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
    resources = concat(
      local.bda_project_arns,
      [
        "arn:aws:bedrock:*:${local.account_id}:data-automation-invocation/*",
        "arn:aws:bedrock:*:*:blueprint/*",
        "arn:aws:bedrock:*:*:data-automation-profile/*",
      ],
    )
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

resource "aws_iam_policy" "document_processor" {
  name   = "${local.service_name}-bedrock-worker"
  policy = data.aws_iam_policy_document.document_processor.json
}

# bda-result-processor: check job status and read blueprints only.
data "aws_iam_policy_document" "bda_result_processor" {
  statement {
    actions = [
      "bedrock:GetDataAutomationStatus",
      "bedrock:GetBlueprint",
    ]
    resources = [
      "arn:aws:bedrock:*:${local.account_id}:data-automation-invocation/*",
      "arn:aws:bedrock:*:*:blueprint/*",
      "arn:aws:bedrock:*:*:data-automation-profile/*",
    ]
  }
}

resource "aws_iam_policy" "bda_result_processor" {
  name   = "${local.service_name}-bedrock-bda-result"
  policy = data.aws_iam_policy_document.bda_result_processor.json
}

# document-reaper: check BDA job status only.
data "aws_iam_policy_document" "bedrock_reaper" {
  statement {
    actions   = ["bedrock:GetDataAutomationStatus"]
    resources = ["arn:aws:bedrock:*:${local.account_id}:data-automation-invocation/*"]
  }
}

resource "aws_iam_policy" "bedrock_reaper" {
  name   = "${local.service_name}-bedrock-reaper"
  policy = data.aws_iam_policy_document.bedrock_reaper.json
}

# --- Cognito ---

# API Lambda only - workers have no user-management paths.
# AdminGetUser, AdminCreateUser, AdminSetUserPassword, AdminInitiateAuth
# are not called anywhere in src - omitted intentionally.
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

# --- Operational services (SSM, SQS, CloudWatch) ---

# API Lambda: SSM read, SQS send-only, CloudWatch.
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

# document-processor and bda-result-processor: SQS send, CloudWatch, SSM.
# SQS receive/delete for metrics-processor is handled by the worker module's inline sqs_access policy.
data "aws_iam_policy_document" "metrics_producer" {
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

resource "aws_iam_policy" "metrics_producer" {
  name   = "${local.service_name}-metrics-producer"
  policy = data.aws_iam_policy_document.metrics_producer.json
}

# metrics-aggregator and usage-report: Athena, Glue, CloudWatch, SSM. No SQS.
data "aws_iam_policy_document" "metrics_aggregator" {
  statement {
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]
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

resource "aws_iam_policy" "metrics_aggregator" {
  name   = "${local.service_name}-pipeline-metrics-aggregator"
  policy = data.aws_iam_policy_document.metrics_aggregator.json
}

# metrics-processor, document-reaper: CloudWatch and SSM only.
data "aws_iam_policy_document" "cloudwatch_ssm" {
  statement {
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]
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

resource "aws_iam_policy" "cloudwatch_ssm" {
  name   = "${local.service_name}-pipeline-cloudwatch-ssm"
  policy = data.aws_iam_policy_document.cloudwatch_ssm.json
}
