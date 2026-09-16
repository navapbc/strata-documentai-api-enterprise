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
  value = var.enable_bedrock_data_automation ? { for k, v in module.bedrock_data_automation : k => v.project_arn } : {}
}

output "bda_profile_arn" {
  value = var.enable_bedrock_data_automation ? module.bedrock_data_automation_all[0].profile_arn : null
}

output "blueprint_arns" {
  description = "ARNs for all custom blueprints created by this project"
  value = var.enable_bedrock_data_automation ? distinct(flatten(concat(
    [for k, v in module.bedrock_data_automation : v.blueprint_arns],
    [module.bedrock_data_automation_all[0].blueprint_arns],
  ))) : []
}

output "cognito_user_pool_id" {
  value = var.enable_identity_provider ? module.identity_provider[0].user_pool_id : null
}

output "cognito_client_id" {
  value = var.enable_identity_provider ? module.identity_provider[0].client_id : null
}

output "admin_ui_bucket" {
  value = var.enable_identity_provider ? module.admin_ui[0].bucket_name : null
}

output "admin_ui_distribution_id" {
  value = var.enable_identity_provider ? module.admin_ui[0].distribution_id : null
}

output "admin_ui_url" {
  value = var.enable_identity_provider ? module.admin_ui[0].url : null
}

output "demo_ui_bucket" {
  value = var.enable_demo_ui ? module.demo_ui[0].bucket_name : null
}

output "demo_ui_distribution_id" {
  value = var.enable_demo_ui ? module.demo_ui[0].distribution_id : null
}

output "demo_ui_url" {
  value = var.enable_demo_ui ? module.demo_ui[0].url : null
}


output "cognito_domain" {
  value = var.enable_identity_provider ? nonsensitive(module.identity_provider[0].user_pool_domain) : null
}

output "cognito_google_enabled" {
  value = var.enable_identity_provider ? nonsensitive(module.identity_provider[0].google_enabled) : null
}
