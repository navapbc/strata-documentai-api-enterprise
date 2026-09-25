_Run: 2026-09-25 16:58 UTC_


## synthetic-insurance-health-insurance-premium-scan.jpg

**Durations**

- bda: 19.48s extraction
- llm: 2.211s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| coverage_end_date | - | 2026-09-30 | 09/30/2026 | 0.91 | 0.8500 | 0.890,0.087,0.081,0.012 | 0.890,0.087,0.081,0.012 | ✅ |
| coverage_start_date | - | 2026-09-01 | 09/01/2026 | 0.82 | 1.0000 | - | 0.791,0.068,0.081,0.011 | ❌ |
| employer_name | - | - | - | 0.94 | - | - | - |  |
| insurer_or_marketplace_name | - | Harbor Health Plan | Harbor Health Plan, Inc. | 0.70 | 1.0000 | 0.135,0.042,0.185,0.045 | 0.352,0.039,0.111,0.012 | ❌ |
| payment_due_date | - | 2026-09-15 | 09/15/2026 | 0.92 | 1.0000 | 0.789,0.103,0.081,0.011 | 0.789,0.103,0.082,0.011 | 🟡 |
| payment_frequency | - | monthly | monthly | 0.86 | 1.0000 | 0.080,0.564,0.055,0.012 | 0.047,0.564,0.325,0.014 | ❌ |
| payment_status | - | Paid | Paid | 0.88 | 1.0000 | 0.729,0.162,0.057,0.015 | 0.729,0.162,0.159,0.016 | ❌ |
| policy_or_member_id | - | HHP123456789 | HHP123456789 | 0.95 | 1.0000 | 0.273,0.321,0.102,0.010 | 0.273,0.322,0.101,0.010 | 🟡 |
| policyholder_name | - | Jordan Rivera | Jordan Rivera | 0.94 | 1.0000 | 0.094,0.192,0.103,0.011 | 0.094,0.192,0.104,0.012 | 🟡 |
| premium_amount | - | 636.25 | 636.25 | 0.95 | 1.0000 | 0.884,0.319,0.062,0.013 | 0.884,0.319,0.062,0.013 | ✅ |
| statement_date | - | 2026-09-01 | 09/01/2026 | 0.91 | 1.0000 | 0.791,0.068,0.081,0.011 | 0.791,0.068,0.081,0.011 | ✅ |
| subsidy_or_tax_credit_amount | - | 323.75 | -323.75 | 0.95 | 1.0000 | 0.884,0.269,0.064,0.013 | 0.883,0.269,0.064,0.012 | 🟡 |
