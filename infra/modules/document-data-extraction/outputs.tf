output "project_arn" {
  description = "ARN of the Bedrock Data Automation project."
  value       = awscc_bedrock_data_automation_project.this.project_arn
}

output "profile_arn" {
  description = "ARN of the BDA data-automation profile used to invoke the project."
  value       = "arn:aws:bedrock:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:data-automation-profile/us.data-automation-v1"
}

output "blueprint_arns" {
  description = "ARNs of all custom blueprints created by this project."
  value       = [for bp in awscc_bedrock_blueprint.this : bp.blueprint_arn]
}

output "access_policy_arn" {
  description = "ARN of the IAM policy granting invoke/read access to the BDA project."
  value       = aws_iam_policy.access.arn
}