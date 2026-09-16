# These moved blocks remap bare module addresses to their new count-indexed
# equivalents introduced when enable_* flags were added. Without them, Terraform
# would destroy and recreate every resource in these modules.
#
# Safe to remove once all environments have been applied with all flags = true.

moved {
  from = module.admin_ui
  to   = module.admin_ui[0]
}

moved {
  from = module.demo_ui
  to   = module.demo_ui[0]
}

moved {
  from = module.identity_provider
  to   = module.identity_provider[0]
}

moved {
  from = module.analytics
  to   = module.analytics[0]
}

moved {
  from = module.monitoring
  to   = module.monitoring[0]
}

moved {
  from = module.bedrock_data_automation_all
  to   = module.bedrock_data_automation_all[0]
}
