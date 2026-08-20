# Document Types

Each folder is a Bedrock Data Automation  (BDA) project category. `managed_blueprints.json` lists AWS-managed blueprint ARNs for that category. Custom blueprint schemas are the remaining `*.json` files.

The `all` project (defined separately in Terraform) unions every folder's custom and managed blueprints.

> **Note:** AWS (BDA) has a limit of 40 blueprints per project. This structure is designed to accommodate the limit and inform application preclassification, project-based routing.

---

## account_statements
| Type | Blueprint |
|------|-----------|
| AWS-Managed | bank-statement |

## dependent_income
| Type | Blueprint |
|------|-----------|
| Custom | alimony-decree |
| Custom | child-support-document |

## education
| Type | Blueprint |
|------|-----------|
| Custom | school-financial-aid-award |

## employer_income
| Type | Blueprint |
|------|-----------|
| AWS-Managed | w2-form |
| AWS-Managed | form-1040 |
| AWS-Managed | form-1099-int |
| AWS-Managed | form-1099-misc |
| AWS-Managed | payslip |
| AWS-Managed | form-1040-schedule-c |

## employment_records
| Type | Blueprint |
|------|-----------|
| AWS-Managed | workers-compensation-form |
| Custom | employment-termination-letter |
| Custom | employment-verification-letter |
| Custom | new-hire-form |
| Custom | proof-of-lost-health-coverage |

## government_benefit_income
| Type | Blueprint |
|------|-----------|
| Custom | unemployment-insurance-claim |
| Custom | va-benefit-letter |

## identity
| Type | Blueprint |
|------|-----------|
| AWS-Managed | us-driver-license |
| AWS-Managed | us-passport |
| AWS-Managed | birth-certificate |
| Custom | i-766-work-authorization |
| Custom | i20-student-visa |
| Custom | i94-arrival-and-departure |
| Custom | social-security-card |

## insurance
| Type | Blueprint |
|------|-----------|
| Custom | insurance-company-letter |

## investment_and_royalty_income
| Type | Blueprint |
|------|-----------|
| Custom | ira-account-document |
| Custom | royalty-statement |

## invoices
| Type | Blueprint |
|------|-----------|
| AWS-Managed | invoice |

## receipts
| Type | Blueprint |
|------|-----------|
| AWS-Managed | receipt |

## retirement_income
| Type | Blueprint |
|------|-----------|
| Custom | annuity-statement |
| Custom | pension-verification |
| Custom | social-security-verification |

## self_employment_income
| Type | Blueprint |
|------|-----------|
| Custom | 1099-consolidated-summary |

## shelter
| Type | Blueprint |
|------|-----------|
| Custom | household-contribution-statement |
| Custom | mortgage-statement |
| Custom | rent-lease-statement |
