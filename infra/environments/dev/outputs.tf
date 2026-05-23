output "api_endpoint" {
  value = var.use_lambda_api ? module.api_gateway[0].api_endpoint : module.service[0].alb_dns_name
}

output "ecr_repository_url" {
  value = module.ecr.repository_url
}

output "region" {
  value = var.region
}

output "document_metadata_table" {
  value = module.document_metadata.table_name
}

output "audit_events_table" {
  value = module.audit_events.table_name
}

output "input_bucket" {
  value = module.input_bucket.bucket_name
}

output "output_bucket" {
  value = module.output_bucket.bucket_name
}

output "bda_project_arns" {
  value = { for k, v in module.bedrock_data_automation : k => v.project_arn }
}

output "cognito_user_pool_id" {
  value = module.identity_provider.user_pool_id
}

output "cognito_client_id" {
  value = module.identity_provider.client_id
}


