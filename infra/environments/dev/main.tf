terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.81.0, < 6.0.0"
    }
    awscc = {
      source  = "hashicorp/awscc"
      version = ">= 1.63.0"
    }
  }

  backend "s3" {
    encrypt = true
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      project     = var.project_name
      environment = var.environment
      managed_by  = "terraform"
    }
  }
}

provider "aws" {
  alias  = "bda"
  region = var.bda_region
}

provider "awscc" {
  alias  = "bda"
  region = var.bda_region
}

data "aws_caller_identity" "current" {}

locals {
  account_id   = data.aws_caller_identity.current.account_id
  service_name = "${var.project_name}-${var.environment}-${local.account_id}"

  # SSM
  ssm_prefix                    = "/${var.project_name}/${var.environment}"
  ssm_classification_prompt_key = "bedrock-classification-prompt"

  # Glue — table name comes from analytics module output

  # App defaults
  max_bda_invoke_retry_attempts = "3"
  api_auth_enabled              = "true"
  api_auth_cache_ttl            = "300"

  # DynamoDB GSI names — single source of truth for infra + env vars
  gsi_job_id               = "JobIdIndex"
  gsi_external_document_id = "ExternalDocumentIdIndex"
  gsi_tenant_id            = "TenantIdIndex"
  gsi_status_created_at    = "StatusCreatedAtIndex"
  gsi_tenant_batches       = "TenantIndex"
  gsi_tenant_builds        = "TenantIndex"
  gsi_external_ref_id      = "ExternalReferenceIdIndex"
}

# --- Networking ---

module "vpc" {
  count  = var.create_vpc ? 1 : 0
  source = "../../modules/vpc"
  name   = "${var.project_name}-${var.environment}"
}

module "networking" {
  count    = var.create_vpc ? 0 : 1
  source   = "../../modules/networking"
  vpc_name = var.vpc_name
}

locals {
  vpc_id             = var.create_vpc ? module.vpc[0].vpc_id : module.networking[0].vpc_id
  private_subnet_ids = var.create_vpc ? module.vpc[0].private_subnet_ids : module.networking[0].private_subnet_ids
  public_subnet_ids  = var.create_vpc ? module.vpc[0].public_subnet_ids : module.networking[0].public_subnet_ids
}

# --- ECR ---

module "ecr" {
  source = "../../modules/container-image-repository"
  name   = "${var.project_name}-${var.environment}"
}

# --- Storage ---

module "input_bucket" {
  source                         = "../../modules/storage"
  name                           = "${local.service_name}-dde-input"
  service_principals_with_access = ["bedrock.amazonaws.com"]

  lifecycle_rules = [{
    id              = "expire-processed"
    expiration_days = 7
  }]
}

module "output_bucket" {
  source                         = "../../modules/storage"
  name                           = "${local.service_name}-dde-output"
  service_principals_with_access = ["bedrock.amazonaws.com"]

  lifecycle_rules = [{
    id              = "expire-results"
    expiration_days = 90
  }]
}

# --- DynamoDB ---

module "document_metadata" {
  source        = "../../modules/nosql"
  table_name    = "${local.service_name}-document-metadata"
  hash_key      = "fileName"
  ttl_attribute = "ttl"

  global_secondary_indexes = [
    {
      name          = local.gsi_job_id
      hash_key      = "jobId"
      hash_key_type = "S"
    },
    {
      name          = local.gsi_external_document_id
      hash_key      = "externalDocumentId"
      hash_key_type = "S"
    },
    {
      name          = local.gsi_tenant_id
      hash_key      = "tenantId"
      hash_key_type = "S"
      sort_key      = "createdAt"
      sort_key_type = "S"
    },
  ]
}

module "api_keys" {
  source     = "../../modules/nosql"
  table_name = "${local.service_name}-api-keys"
  hash_key   = "keyHash"
}


module "tenants" {
  source     = "../../modules/nosql"
  table_name = "${local.service_name}-tenants"
  hash_key   = "tenantId"
}

module "audit_events" {
  source        = "../../modules/nosql"
  table_name    = "${local.service_name}-audit-events"
  hash_key      = "tenantId"
  sort_key      = "timestamp#eventId"
  ttl_attribute = "ttl"

  global_secondary_indexes = [
    {
      name          = "action-timestamp-index"
      hash_key      = "action"
      hash_key_type = "S"
      sort_key      = "timestamp#eventId"
      sort_key_type = "S"
    }
  ]
}
module "extraction_rules" {
  source     = "../../modules/nosql"
  table_name = "${local.service_name}-extraction-rules"
  hash_key   = "tenantId"
  sort_key   = "documentType"
}

module "document_batches" {
  source        = "../../modules/nosql"
  table_name    = "${local.service_name}-document-batches"
  hash_key      = "batchId"
  ttl_attribute = "ttl"

  global_secondary_indexes = [
    {
      name          = local.gsi_status_created_at
      hash_key      = "batchStatus"
      hash_key_type = "S"
      sort_key      = "createdAt"
      sort_key_type = "S"
    },
    {
      name          = local.gsi_tenant_batches
      hash_key      = "tenantId"
      hash_key_type = "S"
      sort_key      = "createdAt"
      sort_key_type = "S"
    },
  ]
}

module "document_builds" {
  source        = "../../modules/nosql"
  table_name    = "${local.service_name}-document-builds"
  hash_key      = "buildId"
  sort_key      = "pageNumber"
  sort_key_type = "N"
  ttl_attribute = "ttl"

  global_secondary_indexes = [
    {
      name          = local.gsi_tenant_builds
      hash_key      = "tenantId"
      hash_key_type = "S"
      sort_key      = "createdAt"
      sort_key_type = "S"
    },
    {
      name          = local.gsi_external_ref_id
      hash_key      = "externalReferenceId"
      hash_key_type = "S"
    },
  ]
}

# --- SQS (Metrics Pipeline) ---

module "metrics_queue" {
  source = "../../modules/queue"
  name   = "${local.service_name}-metrics"
}

# --- Analytics (Athena + Glue) ---

module "metrics_bucket" {
  source = "../../modules/storage"
  name   = "${local.service_name}-metrics"

  lifecycle_rules = [{
    id                    = "archive-metrics"
    transition_to_ia_days = 30
    expiration_days       = 365
  }]
}

module "analytics" {
  source              = "../../modules/analytics"
  name                = "${local.service_name}-analytics"
  results_bucket_name = "${local.service_name}-athena-results"
  metrics_bucket_name = module.metrics_bucket.bucket_name
}

# --- Config (SSM Parameters) ---

module "config" {
  source = "../../modules/config"
  prefix = local.ssm_prefix

  parameters = {
    (local.ssm_classification_prompt_key) = join("\n", [
      "Analyze this image. Respond in JSON only:",
      "{\"document_type\": \"string\", \"confidence\": float 0-1, \"document_count\": int, \"is_blurry\": bool}",
      "ONLY use one of these exact values for document_type: <<DOCUMENT_TYPES>>",
      "Do not create new categories. If unsure, use 'other_document'.",
      "If the image is a photograph, scenery, artwork, or contains no structured text, use 'not_a_document'.",
      "Use 'other_document' ONLY for documents that don't match any listed type.",
      "Set is_blurry to true ONLY if the image appears out of focus, smeared, or motion-blurred.",
      "If is_blurry is true, set confidence below 0.5.",
      "document_count: how many separate documents are visible in this image?",
    ])
  }
}

# --- Identity Provider (Cognito) ---

module "identity_provider" {
  source = "../../modules/identity-provider"
  name   = "${local.service_name}-console"

  callback_urls = [
    "http://localhost:3000/callback",
    "https://${local.service_name}-console.${var.region}.amazonaws.com/callback",
  ]
  logout_urls = [
    "http://localhost:3000",
  ]
}

# --- Secrets ---

module "secrets" {
  source = "../../modules/secrets"

  secrets = {
    API_AUTH_INSECURE_SHARED_KEY = {
      manage_method     = "generated"
      secret_store_name = "/${var.project_name}/${var.environment}/api-auth-insecure-shared-key"
    }
  }
}

# --- Bedrock Data Automation (one project per category) ---

module "bedrock_data_automation" {
  for_each = var.bda_projects
  source   = "../../modules/document-data-extraction"

  providers = {
    aws   = aws.bda
    awscc = awscc.bda
  }

  name = "${local.service_name}-${each.key}"

  blueprints = concat(
    # Custom document type schemas from category folder
    [for f in fileset("${path.module}/../../custom-document-types/${each.key}", "*.json") : "${path.module}/../../custom-document-types/${each.key}/${f}"],
    # AWS managed blueprints for this category
    each.value.managed_blueprint_arns,
  )

  standard_output_configuration = {
    document = {
      extraction = {
        granularity  = { types = ["PAGE"] }
        bounding_box = { state = "ENABLED" }
      }
      output_format = {
        additional_file_format = { state = "DISABLED" }
        text_format            = { types = ["PLAIN_TEXT"] }
      }
    }
    image = {
      extraction = {
        bounding_box = { state = "ENABLED" }
        category     = { state = "ENABLED", types = ["TEXT_DETECTION", "LOGOS"] }
      }
      generative_field = { state = "ENABLED", types = ["IMAGE_SUMMARY"] }
    }
  }

  tags = {
    project     = var.project_name
    environment = var.environment
    category    = each.key
  }
}


# --- API (ECS Fargate + ALB or API Gateway + Lambda) ---

module "service" {
  count  = var.use_lambda_api ? 0 : 1
  source = "../../modules/service"

  service_name         = local.service_name
  vpc_id               = local.vpc_id
  private_subnet_ids   = local.private_subnet_ids
  public_subnet_ids    = local.public_subnet_ids
  image_repository_url = module.ecr.repository_url
  image_tag            = var.image_tag
  cpu                  = var.cpu
  memory               = var.memory
  desired_count        = var.desired_count

  environment_variables = local.lambda_env_vars

  extra_policy_arns = local.lambda_policy_arns

  file_upload_jobs = var.use_lambda_workers ? {} : {
    document_processor = {
      source_bucket = module.input_bucket.bucket_name
      path_prefix   = "input/"
      task_command  = ["document_processor", "<object_key>", "<bucket_name>"]
    }
    bda_result_processor = {
      source_bucket = module.output_bucket.bucket_name
      path_prefix   = "processed/"
      task_command  = ["bda_result_processor", "<bucket_name>", "<object_key>"]
    }
  }
}

module "api_gateway" {
  count  = var.use_lambda_api ? 1 : 0
  source = "../../modules/api-gateway"

  function_name = "${local.service_name}-api"
  image_uri     = "${module.ecr.repository_url}:${var.image_tag}"
  timeout       = 30
  memory_size   = 1024

  environment_variables = local.lambda_env_vars

  policy_arns = local.lambda_policy_arns
}

# --- Lambda Workers (when job_compute_type = "lambda") ---

locals {
  lambda_image_uri = "${module.ecr.repository_url}:${var.image_tag}"

  lambda_env_vars = {
    ENVIRONMENT                                             = var.environment
    DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME                 = module.document_metadata.table_name
    DOCUMENTAI_DOCUMENT_METADATA_JOB_ID_INDEX_NAME          = local.gsi_job_id
    DOCUMENTAI_DOCUMENT_METADATA_EXTERNAL_DOC_ID_INDEX_NAME = local.gsi_external_document_id
    DOCUMENTAI_DOCUMENT_METADATA_TENANT_INDEX_NAME          = local.gsi_tenant_id
    API_KEYS_TABLE_NAME                                     = module.api_keys.table_name
    TENANTS_TABLE_NAME                                      = module.tenants.table_name
    AUDIT_EVENTS_TABLE_NAME                                  = module.audit_events.table_name
    EXTRACTION_RULES_TABLE_NAME                             = module.extraction_rules.table_name
    DOCUMENTAI_BATCH_TABLE_NAME                             = module.document_batches.table_name
    DOCUMENTAI_DOCUMENT_BUILD_TABLE_NAME                    = module.document_builds.table_name
    DOCUMENTAI_INPUT_LOCATION                               = "s3://${module.input_bucket.bucket_name}/input"
    DOCUMENTAI_OUTPUT_LOCATION                              = "s3://${module.output_bucket.bucket_name}"
    DDB_METRICS_INPUT_QUEUE_URL                             = module.metrics_queue.queue_url
    DDB_EXPORT_BUCKET_NAME                                  = module.metrics_bucket.bucket_name
    DDB_RAW_DATA_TABLE_NAME                                 = module.analytics.raw_metrics_table_name
    GLUE_DATABASE_NAME                                      = module.analytics.database_name
    ATHENA_WORKGROUP_NAME                                   = module.analytics.workgroup_name
    BDA_PROJECT_ARNS                                        = jsonencode({ for k, v in module.bedrock_data_automation : k => v.project_arn })
    BDA_PROFILE_ARNS                                        = jsonencode({ for k, v in module.bedrock_data_automation : k => v.profile_arn })
    BDA_PROJECT_ARN                                         = module.bedrock_data_automation["income"].project_arn
    BDA_PROFILE_ARN                                         = module.bedrock_data_automation["income"].profile_arn
    BDA_REGION                                              = var.bda_region
    BEDROCK_CLASSIFICATION_PROMPT_PARAM                     = "${local.ssm_prefix}/${local.ssm_classification_prompt_key}"
    BEDROCK_CLASSIFICATION_MODEL_ID                         = "us.amazon.nova-lite-v1:0"
    SSM_PREFIX                                              = local.ssm_prefix
    MAX_BDA_INVOKE_RETRY_ATTEMPTS                           = local.max_bda_invoke_retry_attempts
    API_AUTH_ENABLED                                        = local.api_auth_enabled
    API_AUTH_ALLOW_INSECURE_FALLBACK                        = "true"
    API_AUTH_CACHE_TTL                                      = local.api_auth_cache_ttl
    API_AUTH_INSECURE_SHARED_KEY_PARAM                      = "/${var.project_name}/${var.environment}/api-auth-insecure-shared-key"
    COGNITO_USER_POOL_ID                                    = module.identity_provider.user_pool_id
    COGNITO_CLIENT_ID                                       = module.identity_provider.client_id
  }

  lambda_policy_arns = {
    data_access         = aws_iam_policy.data_access.arn
    storage_access      = aws_iam_policy.storage_access.arn
    bedrock_access      = aws_iam_policy.bedrock_all.arn
    supporting_services = aws_iam_policy.supporting_services.arn
  }
}

# --- Consolidated IAM Policies (4 policies instead of 15+) ---

data "aws_iam_policy_document" "data_access" {
  # All DynamoDB tables + KMS keys
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
    resources = [
      "${module.document_metadata.table_arn}",
      "${module.document_metadata.table_arn}/index/*",
      "${module.api_keys.table_arn}",
      "${module.api_keys.table_arn}/index/*",
      "${module.tenants.table_arn}",
      "${module.tenants.table_arn}/index/*",
      "${module.extraction_rules.table_arn}",
      "${module.extraction_rules.table_arn}/index/*",
      "${module.document_batches.table_arn}",
      "${module.document_batches.table_arn}/index/*",
      "${module.document_builds.table_arn}",
      "${module.document_builds.table_arn}/index/*",
      "${module.audit_events.table_arn}",
      "${module.audit_events.table_arn}/index/*",
    ]
  }

  statement {
    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
      "kms:GenerateDataKey",
    ]
    resources = ["arn:aws:kms:${var.region}:${local.account_id}:key/*"]
  }
}

resource "aws_iam_policy" "data_access" {
  name   = "${local.service_name}-data-access"
  policy = data.aws_iam_policy_document.data_access.json
}

data "aws_iam_policy_document" "storage_access" {
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

resource "aws_iam_policy" "storage_access" {
  name   = "${local.service_name}-storage-access"
  policy = data.aws_iam_policy_document.storage_access.json
}

data "aws_iam_policy_document" "bedrock_all" {
  # BDA project access
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
      "arn:aws:bedrock:*:${local.account_id}:data-automation-project/*",
      "arn:aws:bedrock:*:*:blueprint/*",
      "arn:aws:bedrock:*:*:data-automation-profile/*",
    ]
  }

  # Bedrock Runtime (Converse API)
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
}

resource "aws_iam_policy" "bedrock_all" {
  name   = "${local.service_name}-bedrock-access"
  policy = data.aws_iam_policy_document.bedrock_all.json
}

data "aws_iam_policy_document" "supporting_services" {
  # SQS
  statement {
    actions = [
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
    ]
    resources = [module.metrics_queue.queue_arn]
  }

  # SSM
  statement {
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:GetParametersByPath",
    ]
    resources = ["arn:aws:ssm:${var.region}:${local.account_id}:parameter${local.ssm_prefix}/*"]
  }

  # Athena
  statement {
    actions = [
      "athena:StartQueryExecution",
      "athena:GetQueryExecution",
      "athena:GetQueryResults",
      "athena:StopQueryExecution",
    ]
    resources = ["arn:aws:athena:${var.region}:${local.account_id}:workgroup/${local.service_name}-analytics"]
  }

  # Cognito
  statement {
    actions = [
      "cognito-idp:AdminInitiateAuth",
      "cognito-idp:AdminGetUser",
      "cognito-idp:AdminCreateUser",
      "cognito-idp:AdminSetUserPassword",
      "cognito-idp:ListUsers",
      # User-management endpoints (super-admin only):
      "cognito-idp:AdminListGroupsForUser",
      "cognito-idp:AdminAddUserToGroup",
      "cognito-idp:AdminRemoveUserFromGroup",
      "cognito-idp:AdminUpdateUserAttributes",
      "cognito-idp:AdminDeleteUserAttributes",
      "cognito-idp:AdminDeleteUser",
    ]
    resources = ["arn:aws:cognito-idp:${var.region}:${local.account_id}:userpool/*"]
  }

  # Glue
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

resource "aws_iam_policy" "supporting_services" {
  name   = "${local.service_name}-supporting-services"
  policy = data.aws_iam_policy_document.supporting_services.json
}

module "document_processor_lambda" {
  count  = var.use_lambda_workers ? 1 : 0
  source = "../../modules/worker"

  function_name         = "${local.service_name}-document-processor"
  image_uri             = local.lambda_image_uri
  command               = ["documentai_api.jobs.document_processor.handler.handler"]
  timeout               = 300
  memory_size           = 512
  environment_variables = local.lambda_env_vars
  policy_arns           = local.lambda_policy_arns

  sqs_trigger = {
    source_bucket = module.input_bucket.bucket_name
    path_prefix   = "input/"
  }
}

module "bda_result_processor_lambda" {
  count  = var.use_lambda_workers ? 1 : 0
  source = "../../modules/worker"

  function_name         = "${local.service_name}-bda-result-processor"
  image_uri             = local.lambda_image_uri
  command               = ["documentai_api.jobs.bda_result_processor.handler.handler"]
  timeout               = 300
  memory_size           = 512
  environment_variables = local.lambda_env_vars
  policy_arns           = local.lambda_policy_arns

  sqs_trigger = {
    source_bucket = module.output_bucket.bucket_name
    path_prefix   = "processed/"
  }
}

module "metrics_processor_lambda" {
  count  = var.use_lambda_workers ? 1 : 0
  source = "../../modules/worker"

  function_name         = "${local.service_name}-metrics-processor"
  image_uri             = local.lambda_image_uri
  command               = ["documentai_api.jobs.metrics_processor.handler.handler"]
  timeout               = 300
  memory_size           = 512
  environment_variables = local.lambda_env_vars
  policy_arns           = local.lambda_policy_arns
}

module "metrics_aggregator_lambda" {
  count  = var.use_lambda_workers ? 1 : 0
  source = "../../modules/worker"

  function_name         = "${local.service_name}-metrics-aggregator"
  image_uri             = local.lambda_image_uri
  command               = ["documentai_api.jobs.metrics_aggregator.handler.handler"]
  timeout               = 300
  memory_size           = 512
  environment_variables = local.lambda_env_vars
  policy_arns           = local.lambda_policy_arns

  schedule_expression = "rate(1 day)"
}
