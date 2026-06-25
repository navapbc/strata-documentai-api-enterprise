# --- S3 bucket for Athena query results ---

module "results_bucket" {
  source       = "../storage"
  name         = var.results_bucket_name
  is_temporary = var.is_temporary

  lifecycle_rules = [{
    id              = "expire-query-results"
    expiration_days = 7
  }]
}

# --- Glue Database ---

resource "aws_glue_catalog_database" "this" {
  name = replace(var.name, "-", "_")
  tags = var.tags
}

# --- Athena Workgroup ---

resource "aws_athena_workgroup" "this" {
  name          = var.name
  force_destroy = var.is_temporary
  tags          = var.tags

  configuration {
    result_configuration {
      output_location = "s3://${module.results_bucket.bucket_name}/results/"
    }

    enforce_workgroup_configuration = true
  }
}

# --- Glue Table: raw_metrics ---

resource "aws_glue_catalog_table" "raw_metrics" {
  database_name = aws_glue_catalog_database.this.name
  name          = "raw_metrics"

  table_type = "EXTERNAL_TABLE"

  parameters = {
    "classification"                = "json"
    "EXTERNAL"                      = "TRUE"
    "has_encrypted_data"            = "false"
    "projection.enabled"            = "true"
    "projection.date.type"          = "date"
    "projection.date.format"        = "yyyy-MM-dd"
    "projection.date.range"         = "2024-01-01,NOW"
    "projection.date.interval"      = "1"
    "projection.date.interval.unit" = "DAYS"
    "projection.hour.type"          = "integer"
    "projection.hour.range"         = "0,23"
    "projection.hour.digits"        = "2"
    "storage.location.template"     = "s3://${var.metrics_bucket_name}/raw/utc/date=$${date}/hour=$${hour}/"
  }

  storage_descriptor {
    location      = "s3://${var.metrics_bucket_name}/raw/utc/"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.openx.data.jsonserde.JsonSerDe"
    }

    columns {
      name = "file_name"
      type = "string"
    }
    columns {
      name = "job_id"
      type = "string"
    }
    columns {
      name = "trace_id"
      type = "string"
    }
    columns {
      name = "user_provided_document_category"
      type = "string"
    }
    columns {
      name = "tenant_id"
      type = "string"
    }
    columns {
      name = "process_status"
      type = "string"
    }
    columns {
      name = "bda_invocation_arn"
      type = "string"
    }
    columns {
      name = "bda_output_s3_uri"
      type = "string"
    }
    columns {
      name = "error_message"
      type = "string"
    }
    columns {
      name = "response_json"
      type = "string"
    }
    columns {
      name = "response_code"
      type = "string"
    }
    columns {
      name = "v1_api_response_json"
      type = "string"
    }
    columns {
      name = "processed_date"
      type = "string"
    }
    columns {
      name = "created_at"
      type = "string"
    }
    columns {
      name = "updated_at"
      type = "string"
    }
    columns {
      name = "bda_started_at"
      type = "string"
    }
    columns {
      name = "bda_completed_at"
      type = "string"
    }
    columns {
      name = "total_processing_time_seconds"
      type = "double"
    }
    columns {
      name = "bda_processing_time_seconds"
      type = "double"
    }
    columns {
      name = "bda_wait_time_seconds"
      type = "double"
    }
    columns {
      name = "file_size_bytes"
      type = "bigint"
    }
    columns {
      name = "content_type"
      type = "string"
    }
    columns {
      name = "pages_detected"
      type = "int"
    }
    columns {
      name = "is_document_blurry"
      type = "string"
    }
    columns {
      name = "is_password_protected"
      type = "string"
    }
    columns {
      name = "additional_info"
      type = "string"
    }
    columns {
      name = "retry_count"
      type = "int"
    }
    columns {
      name = "field_confidence_scores"
      type = "string"
    }
    columns {
      name = "bda_region_used"
      type = "string"
    }
    columns {
      name = "bda_project_arn"
      type = "string"
    }
    columns {
      name = "preclassification_category"
      type = "string"
    }
    columns {
      name = "preclassification_confidence"
      type = "double"
    }
    columns {
      name = "upload_method"
      type = "string"
    }
    columns {
      name = "api_key_name"
      type = "string"
    }
    columns {
      name = "original_file_name"
      type = "string"
    }
    columns {
      name = "matched_blueprint_name"
      type = "string"
    }
    columns {
      name = "matched_blueprint_confidence"
      type = "double"
    }
    columns {
      name = "bda_matched_document_class"
      type = "string"
    }
    columns {
      name = "matched_blueprint_field_empty_list"
      type = "string"
    }
    columns {
      name = "matched_blueprint_field_below_threshold_list"
      type = "string"
    }
    columns {
      name = "matched_blueprint_field_count"
      type = "int"
    }
    columns {
      name = "matched_blueprint_field_count_not_empty"
      type = "int"
    }
    columns {
      name = "matched_blueprint_field_not_empty_avg_confidence"
      type = "double"
    }
    columns {
      name = "preclassification_input_tokens"
      type = "int"
    }
    columns {
      name = "preclassification_output_tokens"
      type = "int"
    }
    columns {
      name = "preclassification_duration_seconds"
      type = "double"
    }
    columns {
      name = "preclassification_model_id"
      type = "string"
    }
    columns {
      name = "crop_bounding_box"
      type = "string"
    }
    columns {
      name = "crop_retained_percentage"
      type = "double"
    }
    columns {
      name = "crop_duration_seconds"
      type = "double"
    }
    columns {
      name = "crop_input_tokens"
      type = "int"
    }
    columns {
      name = "crop_output_tokens"
      type = "int"
    }
    columns {
      name = "crop_model_id"
      type = "string"
    }
    columns {
      name = "grayscale_conversion"
      type = "boolean"
    }
    columns {
      name = "processed_file_size_bytes"
      type = "bigint"
    }
  }

  partition_keys {
    name = "date"
    type = "string"
  }

  partition_keys {
    name = "hour"
    type = "string"
  }
}

# --- IAM Policy ---

data "aws_iam_policy_document" "access" {
  statement {
    actions = [
      "athena:StartQueryExecution",
      "athena:GetQueryExecution",
      "athena:GetQueryResults",
      "athena:StopQueryExecution",
    ]
    resources = [aws_athena_workgroup.this.arn]
  }

  statement {
    actions = [
      "glue:GetTable",
      "glue:GetDatabase",
      "glue:GetPartitions",
    ]
    resources = [
      aws_glue_catalog_database.this.arn,
      "arn:aws:glue:*:*:catalog",
      "arn:aws:glue:*:*:table/${aws_glue_catalog_database.this.name}/*",
    ]
  }

  statement {
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]
    resources = [
      module.results_bucket.bucket_arn,
      "${module.results_bucket.bucket_arn}/*",
    ]
  }
}

resource "aws_iam_policy" "access" {
  name   = "${var.name}-analytics-access"
  policy = data.aws_iam_policy_document.access.json
}
