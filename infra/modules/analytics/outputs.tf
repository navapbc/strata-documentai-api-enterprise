output "raw_metrics_table_name" {
  description = "Name of the Glue catalog table over the raw metrics data."
  value       = aws_glue_catalog_table.raw_metrics.name
}

output "workgroup_name" {
  description = "Name of the Athena workgroup used to query metrics."
  value       = aws_athena_workgroup.this.name
}

output "database_name" {
  description = "Name of the Glue catalog database."
  value       = aws_glue_catalog_database.this.name
}

output "results_bucket_name" {
  description = "Name of the S3 bucket holding Athena query results."
  value       = module.results_bucket.bucket_name
}

output "access_policy_arn" {
  description = "ARN of the IAM policy granting query/read access to the analytics resources."
  value       = aws_iam_policy.access.arn
}

output "results_bucket_arn" {
  description = "ARN of the S3 bucket holding Athena query results."
  value       = module.results_bucket.bucket_arn
}
