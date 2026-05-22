variable "name" {
  type        = string
  description = "Bucket name"
}

variable "is_temporary" {
  type    = bool
  default = false
}

variable "service_principals_with_access" {
  type    = list(string)
  default = []
}

variable "lifecycle_rules" {
  type = list(object({
    id                         = string
    prefix                     = optional(string, "")
    expiration_days            = optional(number)
    transition_to_ia_days      = optional(number)
    transition_to_glacier_days = optional(number)
  }))
  default = []
}

resource "aws_s3_bucket" "this" {
  bucket        = var.name
  force_destroy = var.is_temporary
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket                  = aws_s3_bucket.this.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "this" {
  count  = length(var.lifecycle_rules) > 0 ? 1 : 0
  bucket = aws_s3_bucket.this.id

  dynamic "rule" {
    for_each = var.lifecycle_rules
    content {
      id     = rule.value.id
      status = "Enabled"

      filter {
        prefix = rule.value.prefix
      }

      dynamic "transition" {
        for_each = rule.value.transition_to_ia_days != null ? [1] : []
        content {
          days          = rule.value.transition_to_ia_days
          storage_class = "STANDARD_IA"
        }
      }

      dynamic "transition" {
        for_each = rule.value.transition_to_glacier_days != null ? [1] : []
        content {
          days          = rule.value.transition_to_glacier_days
          storage_class = "GLACIER"
        }
      }

      dynamic "expiration" {
        for_each = rule.value.expiration_days != null ? [1] : []
        content {
          days = rule.value.expiration_days
        }
      }
    }
  }
}

# EventBridge notifications for S3 events (used by file upload jobs)
resource "aws_s3_bucket_notification" "this" {
  bucket      = aws_s3_bucket.this.id
  eventbridge = true
}

# Access policy for the service to read/write
data "aws_iam_policy_document" "access" {
  statement {
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.this.arn,
      "${aws_s3_bucket.this.arn}/*",
    ]
  }
}

resource "aws_iam_policy" "access" {
  name   = "${var.name}-access"
  policy = data.aws_iam_policy_document.access.json
}

# Bucket policy for service principals (e.g. bedrock.amazonaws.com)
data "aws_iam_policy_document" "bucket_policy" {
  count = length(var.service_principals_with_access) > 0 ? 1 : 0

  statement {
    principals {
      type        = "Service"
      identifiers = var.service_principals_with_access
    }
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.this.arn,
      "${aws_s3_bucket.this.arn}/*",
    ]
  }
}

resource "aws_s3_bucket_policy" "this" {
  count  = length(var.service_principals_with_access) > 0 ? 1 : 0
  bucket = aws_s3_bucket.this.id
  policy = data.aws_iam_policy_document.bucket_policy[0].json
}

output "bucket_name" {
  value = aws_s3_bucket.this.bucket
}

output "bucket_arn" {
  value = aws_s3_bucket.this.arn
}

output "access_policy_arn" {
  value = aws_iam_policy.access.arn
}
