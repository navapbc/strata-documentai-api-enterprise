# Document Types

Each top-level folder is a Bedrock Data Automation (BDA) project category, also referred to as a **parent category** (or higher-level project). `managed_blueprints.json` lists AWS-managed blueprint ARNs for that category; custom blueprint schemas are the remaining `*.json` files.

Some parent categories hold their blueprints directly (`identity`, `expenses`, `assets`). Others group several leaf document-type folders underneath them (`income`, `supporting_records`) so that related-but-numerous document types can share one BDA project without any single project exceeding AWS's per-project blueprint limit. Terraform (`infra/environments/dev/main.tf`) walks both shapes recursively and creates exactly one BDA project per parent category.

> **Note:** AWS (BDA) has a limit of 40 blueprints per project. Grouping leaf document types under a handful of parent categories keeps every project comfortably under that limit while leaving room to grow - see `document_type_folders` in `infra/environments/dev/main.tf`.

---

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

## expenses
| Type | Blueprint |
|------|-----------|
| AWS-Managed | electricity-bill |
| AWS-Managed | cable-bill |
| AWS-Managed | water-and-sewer-bill |
| Custom | burial |
| Custom | dependent-care |

## assets
| Type | Blueprint |
|------|-----------|
| AWS-Managed | us-vehicle-title-document |
| Custom | life-insurance-policy |
| Custom | miscellaneous-assets |
| Custom | real-estate |
| Custom | trust-fund |

## income
Groups every income-related leaf document type into a single BDA project.

### income/dependent_income
| Type | Blueprint |
|------|-----------|
| Custom | alimony-decree |
| Custom | child-support-document |

### income/employer_income
| Type | Blueprint |
|------|-----------|
| AWS-Managed | w2-form |
| AWS-Managed | form-1040 |
| AWS-Managed | form-1099-int |
| AWS-Managed | form-1099-misc |
| AWS-Managed | payslip |
| AWS-Managed | form-1040-schedule-c |

### income/employment_records
| Type | Blueprint |
|------|-----------|
| AWS-Managed | workers-compensation-form |
| Custom | employment-termination-letter |
| Custom | employment-verification-letter |
| Custom | new-hire-form |
| Custom | proof-of-lost-health-coverage |

### income/government_benefit_income
| Type | Blueprint |
|------|-----------|
| Custom | unemployment-insurance-claim |
| Custom | va-benefit-letter |

### income/investment_and_royalty_income
| Type | Blueprint |
|------|-----------|
| Custom | ira-account-document |
| Custom | royalty-statement |

### income/retirement_income
| Type | Blueprint |
|------|-----------|
| Custom | annuity-statement |
| Custom | pension-verification |
| Custom | social-security-verification |

### income/self_employment_income
| Type | Blueprint |
|------|-----------|
| Custom | 1099-consolidated-summary |

## supporting_records
Groups the remaining lower-volume leaf document types into a single BDA project.

### supporting_records/account_statements
| Type | Blueprint |
|------|-----------|
| AWS-Managed | bank-statement |

### supporting_records/education
| Type | Blueprint |
|------|-----------|
| Custom | school-financial-aid-award |

### supporting_records/insurance
| Type | Blueprint |
|------|-----------|
| Custom | insurance-company-letter |
| Custom | health-insurance-premium-statement |

### supporting_records/invoices
| Type | Blueprint |
|------|-----------|
| AWS-Managed | invoice |

### supporting_records/receipts
| Type | Blueprint |
|------|-----------|
| AWS-Managed | receipt |

### supporting_records/shelter
| Type | Blueprint |
|------|-----------|
| Custom | household-contribution-statement |
| Custom | mortgage-statement |
| Custom | rent-lease-statement |
| Custom | shelter-verification-letter |
| Custom | shelter-payment-receipt |