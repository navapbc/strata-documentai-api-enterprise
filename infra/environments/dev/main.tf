terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.81.0, < 6.61.1"
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
  ssm_prefix = "/${var.project_name}/${var.environment}"

  # S3 path prefixes - single source of truth for env vars + lifecycle rules
  input_prefix       = "input"
  demo_input_prefix  = "${local.input_prefix}/demo"
  output_prefix      = "processed"
  demo_output_prefix = "${local.output_prefix}/${local.demo_input_prefix}"

  # App defaults
  max_bda_invoke_retry_attempts = "3"
  api_auth_enabled              = "true"
  api_auth_cache_ttl            = "300"

  # DynamoDB GSI names - single source of truth for infra + env vars
  gsi_job_id                = "JobIdIndex"
  gsi_external_document_id  = "ExternalDocumentIdIndex"
  gsi_bda_invocation_id     = "BdaInvocationIdIndex"
  gsi_tenant_id             = "TenantIdIndex"
  gsi_status_created_at     = "StatusCreatedAtIndex"
  gsi_tenant_batches        = "TenantIndex"
  gsi_tenant_builds         = "TenantIndex"
  gsi_external_ref_id       = "ExternalReferenceIdIndex"
  gsi_api_keys_tenant_index = "TenantApiKeyNameIndex"
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

  lifecycle_rules = [
    {
      id              = "expire-processed"
      prefix          = "${local.input_prefix}/"
      expiration_days = 7
    },
    {
      id              = "expire-demo-uploads"
      prefix          = "${local.demo_input_prefix}/"
      expiration_days = 7
    },
    {
      id              = "expire-preprocessing-originals"
      prefix          = "preprocessing/"
      expiration_days = 30
    },
    {
      id              = "expire-test-runner"
      prefix          = "test-runner/"
      expiration_days = 7
    },
  ]
}

module "output_bucket" {
  source                         = "../../modules/storage"
  name                           = "${local.service_name}-dde-output"
  service_principals_with_access = ["bedrock.amazonaws.com"]

  lifecycle_rules = [{
    id              = "expire-results"
    expiration_days = 30
    },
    {
      id              = "expire-demo-results"
      prefix          = "${local.demo_output_prefix}/"
      expiration_days = 7
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
      name          = local.gsi_bda_invocation_id
      hash_key      = "bdaInvocationId"
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

  global_secondary_indexes = [
    {
      name          = local.gsi_api_keys_tenant_index
      hash_key      = "tenantId"
      hash_key_type = "S"
      sort_key      = "apiKeyName"
      sort_key_type = "S"
    },
  ]
}


module "tenants" {
  source     = "../../modules/nosql"
  table_name = "${local.service_name}-tenants"
  hash_key   = "tenantId"
}

module "tenant_request_counts" {
  source        = "../../modules/nosql"
  table_name    = "${local.service_name}-tenant-request-counts"
  hash_key      = "tenantId"
  sort_key      = "date"
  ttl_attribute = "ttl"
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
    },
    {
      name          = "actor-email-timestamp-index"
      hash_key      = "actorEmail"
      hash_key_type = "S"
      sort_key      = "timestamp#eventId"
      sort_key_type = "S"
    },
  ]
}
module "extraction_rules" {
  source     = "../../modules/nosql"
  table_name = "${local.service_name}-extraction-rules"
  hash_key   = "tenantId"
  sort_key   = "documentType"
}

module "document_categories" {
  source     = "../../modules/nosql"
  table_name = "${local.service_name}-document-categories"
  hash_key   = "tenantId"
  sort_key   = "categoryName"
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

  lifecycle_rules = [
    {
      id                    = "expire-raw-metrics"
      prefix                = "raw/"
      transition_to_ia_days = 30
      expiration_days       = 365
    },
    {
      id                    = "archive-aggregated"
      prefix                = "aggregated/"
      transition_to_ia_days = 90
    },
    {
      id                    = "archive-usage-reports"
      prefix                = "usage-report/"
      transition_to_ia_days = 30
    },
  ]
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
    "feature-flags/preclassification-based-routing"             = "false"
    "feature-flags/skip-bda-if-unclassified"                    = "false"
    "feature-flags/enable-preclassification-blueprint-matching" = "true"
    "feature-flags/document-crop"                               = "true"
    "feature-flags/textract-identity-enabled"                   = "true"
    "feature-flags/enable-blur-detection"                       = "true"
    "feature-flags/enforce-blur-rejection"                      = "true"
    "feature-flags/include-missing-geo-with-missing-fields"     = "true"
    "feature-flags/flag-multiple-documents-in-multipage"        = "true"
    # Thresholds
    # Vision model ids - swappable at runtime via SSM (no redeploy). Kept as
    # separate params so preclassification and bbox detection can be tuned apart.
    #   Lite  - vision tasks (preclassification, blueprint match: model sees the image)
    #   Pro   - blur empty-quadrant check (spatial reasoning over image crops)
    #   Micro - supplemental extraction: text-only field matching over Textract WORD
    #           blocks (no image sent), cheapest/fastest for basic text-in/text-out
    "models/classification-model-id"          = "us.amazon.nova-pro-v1:0"
    "models/bounding-box-model-id"            = "us.amazon.nova-lite-v1:0"
    "models/blur-quadrant-model-id"           = "us.amazon.nova-pro-v1:0"
    "models/supplemental-extraction-model-id" = "us.amazon.nova-micro-v1:0"
  }

  allowed_patterns = {
    "feature-flags/preclassification-based-routing"             = "^(true|false)$"
    "feature-flags/skip-bda-if-unclassified"                    = "^(true|false)$"
    "feature-flags/enable-preclassification-blueprint-matching" = "^(true|false)$"
    "feature-flags/document-crop"                               = "^(true|false)$"
    "feature-flags/textract-identity-enabled"                   = "^(true|false)$"
    "feature-flags/enable-blur-detection"                       = "^(true|false)$"
    "feature-flags/enforce-blur-rejection"                      = "^(true|false)$"
    "feature-flags/include-missing-geo-with-missing-fields"     = "^(true|false)$"
    "feature-flags/flag-multiple-documents-in-multipage"        = "^(true|false)$"
  }
}

# --- Identity Provider (Cognito) ---

module "admin_ui" {
  source      = "../../modules/static-site"
  name        = "${local.service_name}-admin-ui"
  description = "DocumentAI Admin Console (${var.environment})"
}

module "demo_ui" {
  source      = "../../modules/static-site"
  name        = "${local.service_name}-demo-ui"
  description = "DocumentAI Demo (${var.environment})"
}

module "identity_provider" {
  source = "../../modules/identity-provider"
  name   = "${local.service_name}-console"

  callback_urls = [
    "http://localhost:3000/callback",
    "http://localhost:3001/callback",
    "https://${module.admin_ui.distribution_domain}/callback",
    "https://${module.demo_ui.distribution_domain}/callback",
  ]
  logout_urls = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://${module.admin_ui.distribution_domain}",
    "https://${module.demo_ui.distribution_domain}",
  ]

  # Google SSO: credentials stored in SSM SecureString parameters (created
  # manually via console/CLI, never committed to the repo). Set to null to
  # disable Google sign-in.
  google_client_id_ssm_param     = var.google_sso_enabled ? "/${var.project_name}/${var.environment}/google-oauth-client-id" : null
  google_client_secret_ssm_param = var.google_sso_enabled ? "/${var.project_name}/${var.environment}/google-oauth-client-secret" : null
  google_allowed_domains         = var.google_allowed_domains
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

locals {
  document_type_folders = toset([for f in fileset("${path.module}/../../document-types", "*/managed_blueprints.json") : dirname(f)])

  all_managed_blueprint_arns = distinct(flatten([for folder in local.document_type_folders : [for bp in jsondecode(file("${path.module}/../../document-types/${folder}/managed_blueprints.json")) : bp.arn]]))
}

module "bedrock_data_automation" {
  for_each = local.document_type_folders
  source   = "../../modules/document-data-extraction"

  providers = {
    aws   = aws.bda
    awscc = awscc.bda
  }

  name        = "${local.service_name}-${each.key}"
  description = "BDA project for ${replace(each.key, "_", " ")} documents"

  blueprints = concat(
    [for f in fileset("${path.module}/../../document-types/${each.key}", "*.json") : "${path.module}/../../document-types/${each.key}/${f}"
    if f != "managed_blueprints.json"],
    [for bp in jsondecode(file("${path.module}/../../document-types/${each.key}/managed_blueprints.json")) : bp.arn],
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

module "bedrock_data_automation_all" {
  source = "../../modules/document-data-extraction"

  providers = {
    aws   = aws.bda
    awscc = awscc.bda
  }

  name        = "${local.service_name}-all"
  description = "BDA project for all document types"
  blueprints = concat(
    flatten([for k, v in module.bedrock_data_automation : v.blueprint_arns]),
    local.all_managed_blueprint_arns,
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
    category    = "all"
  }
}


# --- API (API Gateway + Lambda) ---

module "api_gateway" {
  source = "../../modules/api-gateway"

  function_name = "${local.service_name}-api"
  image_uri     = "${module.ecr.repository_url}:${var.image_tag}"
  timeout       = 30
  memory_size   = 1024

  environment_variables = local.api_lambda_env_vars

  policy_arns = local.lambda_policy_arns
}

# --- Lambda Workers ---

locals {
  lambda_image_uri = "${module.ecr.repository_url}:${var.image_tag}"

  # CORS origins are derived from the managed admin/demo CloudFront
  # distributions so they can never drift to a wildcard or a stale value.
  # extra_cors_allowed_origins is the plan/apply injection point for anything
  # not managed here (e.g. http://localhost:3000 during UI development).
  #
  # Enforced by the FastAPI app (Starlette CORSMiddleware), not the gateway:
  # the single $default route forwards OPTIONS preflight to Lambda, so the app
  # is the only layer that can answer it. Passed only to the API Lambda via
  # api_lambda_env_vars below.
  cors_allowed_origins = concat(
    [module.admin_ui.url, module.demo_ui.url],
    var.extra_cors_allowed_origins,
  )

  lambda_env_vars = merge(
    {
      # Per-category project IDs - prefix stripped to save env space. App reconstructs
      # full ARN via BDA_PROJECT_ARN_PREFIX + BDA_PROJECT_ID_{CATEGORY}.
      # Adding/removing a folder in infra/document-types automatically injects/removes its entry.
      for k, v in module.bedrock_data_automation : "BDA_PROJECT_ID_${upper(k)}" => regex("^.*/(.+)$", v.project_arn)[0]
    },
    {
      ENVIRONMENT                                               = var.environment
      DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME                   = module.document_metadata.table_name
      DOCUMENTAI_DOCUMENT_METADATA_JOB_ID_INDEX_NAME            = local.gsi_job_id
      DOCUMENTAI_DOCUMENT_METADATA_EXTERNAL_DOC_ID_INDEX_NAME   = local.gsi_external_document_id
      DOCUMENTAI_DOCUMENT_METADATA_BDA_INVOCATION_ID_INDEX_NAME = local.gsi_bda_invocation_id
      DOCUMENTAI_DOCUMENT_METADATA_TENANT_INDEX_NAME            = local.gsi_tenant_id
      API_KEYS_TABLE_NAME                                       = module.api_keys.table_name
      API_KEYS_TENANT_INDEX_NAME                                = local.gsi_api_keys_tenant_index
      TENANTS_TABLE_NAME                                        = module.tenants.table_name
      TENANT_REQUEST_COUNTS_TABLE_NAME                          = module.tenant_request_counts.table_name
      AUDIT_EVENTS_TABLE_NAME                                   = module.audit_events.table_name
      EXTRACTION_RULES_TABLE_NAME                               = module.extraction_rules.table_name
      DOCUMENT_CATEGORIES_TABLE_NAME                            = module.document_categories.table_name
      DOCUMENTAI_BATCH_TABLE_NAME                               = module.document_batches.table_name
      DOCUMENTAI_DOCUMENT_BUILD_TABLE_NAME                      = module.document_builds.table_name
      DOCUMENTAI_INPUT_LOCATION                                 = "s3://${module.input_bucket.bucket_name}/${local.input_prefix}"
      DOCUMENTAI_DEMO_INPUT_LOCATION                            = "s3://${module.input_bucket.bucket_name}/${local.demo_input_prefix}"
      DOCUMENTAI_PREPROCESSING_LOCATION                         = "s3://${module.input_bucket.bucket_name}/preprocessing"
      DOCUMENTAI_OUTPUT_LOCATION                                = "s3://${module.output_bucket.bucket_name}/processed"
      DDB_METRICS_INPUT_QUEUE_URL                               = module.metrics_queue.queue_url
      DDB_EXPORT_BUCKET_NAME                                    = module.metrics_bucket.bucket_name
      DDB_RAW_DATA_TABLE_NAME                                   = module.analytics.raw_metrics_table_name
      GLUE_DATABASE_NAME                                        = module.analytics.database_name
      ATHENA_WORKGROUP_NAME                                     = module.analytics.workgroup_name
      BDA_PROJECT_ARN_PREFIX                                    = regex("^(.*)/", module.bedrock_data_automation_all.project_arn)[0]
      BDA_PROJECT_ARN_ALL                                       = module.bedrock_data_automation_all.project_arn
      BDA_PROFILE_ARN                                           = module.bedrock_data_automation_all.profile_arn
      BDA_REGION                                                = var.bda_region
      BEDROCK_CLASSIFICATION_MODEL_ID_PARAM                     = "${local.ssm_prefix}/models/classification-model-id"
      BEDROCK_BOUNDING_BOX_MODEL_ID_PARAM                       = "${local.ssm_prefix}/models/bounding-box-model-id"
      BEDROCK_BLUR_QUADRANT_MODEL_ID_PARAM                      = "${local.ssm_prefix}/models/blur-quadrant-model-id"
      BEDROCK_SUPPLEMENTAL_EXTRACTION_MODEL_ID_PARAM            = "${local.ssm_prefix}/models/supplemental-extraction-model-id"
      SSM_PREFIX                                                = local.ssm_prefix
      MAX_BDA_INVOKE_RETRY_ATTEMPTS                             = local.max_bda_invoke_retry_attempts
      API_AUTH_ENABLED                                          = local.api_auth_enabled
      API_AUTH_CACHE_TTL                                        = local.api_auth_cache_ttl
      API_AUTH_INSECURE_SHARED_KEY_PARAM                        = "/${var.project_name}/${var.environment}/api-auth-insecure-shared-key"
      COGNITO_USER_POOL_ID                                      = module.identity_provider.user_pool_id
      COGNITO_CLIENT_ID                                         = module.identity_provider.client_id
      OTEL_SDK_DISABLED                                         = tostring(!var.otel_enabled)
      OTEL_SERVICE_NAME                                         = var.otel_service_name
      OTEL_EXPORTER_OTLP_ENDPOINT                               = var.otel_exporter_otlp_endpoint
      OTEL_AWS_APPLICATION_SIGNALS_ENABLED                      = tostring(var.otel_enabled)
      OTEL_METRICS_EXPORTER                                     = "awsemf"
      OTEL_EXPORTER_OTLP_LOGS_HEADERS                           = "x-aws-metric-namespace=${var.otel_service_name}"
  })

  # API Lambda env: the shared worker map, minus the Athena/Glue vars that only
  # the metrics-aggregator/usage-report workers read, plus CORS_ALLOWED_ORIGINS.
  # BDA_PROJECT_ID_* is also dropped - only the document_processor worker (via
  # bda_invoker.py) and the offline pull-blueprint-schemas CLI (via schemas.py)
  # call get_bda_project_arns(); the API Lambda has no runtime path that does,
  # since get_all_schemas() reads a preloaded static file instead of calling
  # BDA directly. Dropping these keeps the API function under the 4KB Lambda
  # env limit once CORS is added.
  api_lambda_env_vars = merge(
    {
      for k, v in local.lambda_env_vars : k => v
      if !contains(["ATHENA_WORKGROUP_NAME", "GLUE_DATABASE_NAME", "DDB_RAW_DATA_TABLE_NAME"], k)
      && !startswith(k, "BDA_PROJECT_ID_")
    },
    {
      CORS_ALLOWED_ORIGINS = jsonencode(local.cors_allowed_origins)
    },
  )

  lambda_policy_arns = {
    data_access         = aws_iam_policy.data_access.arn
    storage_access      = aws_iam_policy.storage_access.arn
    bedrock_access      = aws_iam_policy.bedrock_all.arn
    supporting_services = aws_iam_policy.supporting_services.arn
  }
}

# --- Monitoring (CloudWatch dashboard + alarms + SNS) ---

module "monitoring" {
  source = "../../modules/monitoring"

  name_prefix  = local.service_name
  project_name = var.project_name
  environment  = var.environment
  region       = var.region

  # Dashboard in every env; alarms controlled by var.create_alarms (default false).
  create_dashboard = true
  create_alarms    = var.create_alarms

  alarm_emails = var.alarm_emails
  slack        = var.slack_config

  # API Gateway
  api_gateway_id  = module.api_gateway.api_id
  api_log_metrics = module.api_gateway.api_log_metrics

  # Worker Lambdas
  workers = {
    "Document Processor"   = { function_name = module.workers["document-processor"].function_name, timeout_seconds = 300, pipeline = true, scheduled = false }
    "BDA Result Processor" = { function_name = module.workers["bda-result-processor"].function_name, timeout_seconds = 300, pipeline = true, scheduled = false }
    "Metrics Processor"    = { function_name = module.workers["metrics-processor"].function_name, timeout_seconds = 300, pipeline = false, scheduled = false }
    "Metrics Aggregator"   = { function_name = module.workers["metrics-aggregator"].function_name, timeout_seconds = 300, pipeline = false, scheduled = true, invocation_window_seconds = 600 }
    # invocation_window_seconds = 86400: current-month cron fires daily, so a full
    # day with zero runs means the schedule is broken. Note: on first apply with
    # create_alarms = true the alarm starts in ALARM until the next daily run lands
    # (~up to 24 hours) - expected bring-up behavior, not a recurring false positive.
    "Usage Report" = { function_name = module.workers["usage-report"].function_name, timeout_seconds = 300, pipeline = false, scheduled = true, invocation_window_seconds = 86400 }
  }

  # API Lambda
  api_lambda_function_name   = module.api_gateway.function_name
  api_lambda_timeout_seconds = 30

  # Queues
  metrics_queue_name          = module.metrics_queue.queue_name
  metrics_queue_dlq_name      = module.metrics_queue.dlq_name
  document_processor_dlq_name = module.workers["document-processor"].dlq_name
  bda_output_dlq_name         = module.workers["bda-result-processor"].dlq_name
}

# --- Consolidated IAM Policies (4 policies instead of 15+) ---

# AWS-managed key ARNs for SSE-KMS access (buckets use aws/s3, SecureString
# params use aws/ssm), resolved so the data-access policy can scope to them.
data "aws_kms_alias" "s3" {
  name = "alias/aws/s3"
}

data "aws_kms_alias" "ssm" {
  name = "alias/aws/ssm"
}

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
  }

  # Scoped to exactly the keys this role touches: the per-table DynamoDB CMKs,
  # the AWS-managed aws/s3 key (SSE-KMS buckets) and the aws/ssm key (SecureString
  # params - API-auth key, Cognito client secret). Dropping any of these breaks
  # table/bucket/param access, so verify after applying.
  statement {
    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
      "kms:GenerateDataKey",
    ]
    resources = concat(
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

  # Textract (AnalyzeID for identity documents, DetectDocumentText for blur detection)
  statement {
    actions = [
      "textract:AnalyzeID",
      "textract:DetectDocumentText",
    ]
    resources = ["*"]
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
      "cognito-idp:ListUsersInGroup",
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

# Workers share all config except their command and trigger. The trigger types
# differ (S3 / SQS / schedule), so they can't live in one map value without making
# the map heterogeneous (which for_each rejects). Instead the command map drives
# for_each and each trigger is resolved from its own homogeneous lookup map.
locals {
  worker_commands = {
    "document-processor"   = ["documentai_api.jobs.document_processor.handler.handler"]
    "bda-result-processor" = ["documentai_api.jobs.bda_result_processor.handler.handler"]
    "metrics-processor"    = ["documentai_api.jobs.metrics_processor.handler.handler"]
    "metrics-aggregator"   = ["documentai_api.jobs.metrics_aggregator.handler.handler"]
    "usage-report"         = ["documentai_api.jobs.usage_report.handler.handler"]
  }
}

module "workers" {
  for_each = local.worker_commands
  source   = "../../modules/worker"

  function_name         = "${local.service_name}-${each.key}"
  image_uri             = local.lambda_image_uri
  command               = each.value
  timeout               = 300
  memory_size           = 1024
  environment_variables = local.lambda_env_vars
  policy_arns           = local.lambda_policy_arns

  s3_trigger = lookup({
    "document-processor"   = { source_bucket = module.input_bucket.bucket_name, path_prefix = "input/" }
    "bda-result-processor" = { source_bucket = module.output_bucket.bucket_name, path_prefix = "processed/", path_suffix = "job_metadata.json" }
  }, each.key, null)

  sqs_trigger = lookup({
    "metrics-processor" = { queue_arn = module.metrics_queue.queue_arn, batch_size = 10, max_batching_window_seconds = 300 }
  }, each.key, null)

  schedules = lookup({
    "metrics-aggregator" = [
      { name = "current-day", schedule_expression = "rate(5 minutes)", input = { mode = "today", overwrite = "true" } },
      { name = "prior-day", schedule_expression = "cron(0 2 * * ? *)", input = { mode = "yesterday", overwrite = "true" } },
    ]
    "usage-report" = [
      { name = "current-month", schedule_expression = "cron(0 6 * * ? *)", input = { month = "current" } },
      { name = "previous-month", schedule_expression = "cron(0 6 1-5 * ? *)", input = { month = "previous" } },
    ]
  }, each.key, [])
}
