# KMS key for encryption
resource "aws_kms_key" "this" {
  description             = "KMS key for ${var.table_name}"
  deletion_window_in_days = 10
  enable_key_rotation     = true
}

locals {
  # Build attribute definitions from hash key, sort key, and GSI keys
  base_attributes = concat(
    [{ name = var.hash_key, type = var.hash_key_type }],
    var.sort_key != null ? [{ name = var.sort_key, type = var.sort_key_type }] : [],
  )

  gsi_attributes = flatten([
    for gsi in var.global_secondary_indexes : concat(
      [{ name = gsi.hash_key, type = gsi.hash_key_type }],
      gsi.sort_key != null ? [{ name = gsi.sort_key, type = gsi.sort_key_type }] : [],
    )
  ])

  # Deduplicate by attribute name (last wins, all same-name attrs have same type)
  all_attributes_map = { for attr in concat(local.base_attributes, local.gsi_attributes) : attr.name => attr... }
  all_attributes     = [for name, attrs in local.all_attributes_map : attrs[0]]
}

resource "aws_dynamodb_table" "this" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = var.hash_key
  range_key    = var.sort_key
  tags         = var.tags

  dynamic "attribute" {
    for_each = local.all_attributes
    content {
      name = attribute.value.name
      type = attribute.value.type
    }
  }

  dynamic "ttl" {
    for_each = var.ttl_attribute != null ? [1] : []
    content {
      attribute_name = var.ttl_attribute
      enabled        = true
    }
  }

  dynamic "global_secondary_index" {
    for_each = var.global_secondary_indexes
    content {
      name            = global_secondary_index.value.name
      hash_key        = global_secondary_index.value.hash_key
      range_key       = global_secondary_index.value.sort_key
      projection_type = global_secondary_index.value.projection_type
    }
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.this.arn
  }

  point_in_time_recovery {
    enabled = true
  }

  deletion_protection_enabled = !var.is_temporary
}

# IAM policy for read/write access
data "aws_iam_policy_document" "access" {
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
      aws_dynamodb_table.this.arn,
      "${aws_dynamodb_table.this.arn}/index/*",
    ]
  }

  statement {
    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
      "kms:GenerateDataKey",
    ]
    resources = [aws_kms_key.this.arn]
  }
}

resource "aws_iam_policy" "access" {
  name   = "${var.table_name}-access"
  policy = data.aws_iam_policy_document.access.json
}
