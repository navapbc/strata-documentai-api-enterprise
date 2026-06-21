output "api_endpoint" {
  value = module.api_gateway.api_endpoint
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

output "api_keys_table" {
  value = module.api_keys.table_name
}

output "tenants_table" {
  value = module.tenants.table_name
}

output "document_metadata_tenant_index_name" {
  value = local.gsi_tenant_id
}

output "document_metadata_job_id_index_name" {
  value = local.gsi_job_id
}

output "document_metadata_bda_invocation_id_index_name" {
  value = local.gsi_bda_invocation_id
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

output "admin_ui_bucket" {
  value = module.admin_ui.bucket_name
}

output "admin_ui_distribution_id" {
  value = module.admin_ui.distribution_id
}

output "admin_ui_url" {
  value = module.admin_ui.url
}

output "demo_ui_bucket" {
  value = module.demo_ui.bucket_name
}

output "demo_ui_distribution_id" {
  value = module.demo_ui.distribution_id
}

output "demo_ui_url" {
  value = module.demo_ui.url
}


output "cognito_domain" {
  value = nonsensitive(module.identity_provider.user_pool_domain)
}

output "cognito_google_enabled" {
  value = nonsensitive(module.identity_provider.google_enabled)
}
