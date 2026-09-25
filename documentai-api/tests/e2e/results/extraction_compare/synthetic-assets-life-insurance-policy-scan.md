_Run: 2026-09-25 16:53 UTC_


## synthetic-assets-life-insurance-policy-scan.jpg

**Durations**

- bda: 22.83s extraction
- llm: 5.207s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| cash_surrender_value | - | 13000 | 13000 | 0.92 | 1.0000 | 0.462,0.516,0.092,0.018 | 0.463,0.517,0.091,0.018 | 🟡 |
| death_benefit | - | 50000 | 50000 | 0.89 | 1.0000 | 0.172,0.515,0.092,0.018 | 0.172,0.515,0.092,0.018 | ✅ |
| insured_name | - | Jordan Rivera | Jordan Rivera | 0.94 | 0.9900 | 0.714,0.394,0.092,0.009 | 0.103,0.264,0.105,0.010 | ❌ |
| insurer_name | - | Northstar Life Insurance Company | Northstar Life Insurance Company | 0.83 | 1.0000 | 0.083,0.144,0.232,0.011 | 0.083,0.144,0.232,0.011 | ✅ |
| policy_number | - | NSL-78XX-45XX-9X21 | NSL-78XX-45XX-9X21 | 0.94 | 0.9800 | 0.304,0.373,0.148,0.010 | 0.304,0.373,0.148,0.010 | ✅ |
| policy_type | - | Whole Life Insurance | Whole Life Insurance | 0.91 | 1.0000 | 0.303,0.391,0.140,0.010 | 0.303,0.392,0.139,0.010 | 🟡 |
| policyholder_name | - | Jordan Rivera | Jordan Rivera | 0.95 | 0.9900 | 0.713,0.376,0.092,0.009 | 0.103,0.264,0.105,0.010 | ❌ |
| premium_amount | - | 175 | 175.00 | 0.95 | 1.0000 | 0.302,0.466,0.053,0.011 | 0.302,0.466,0.053,0.011 | ✅ |
| premium_frequency | - | Monthly | Monthly | 0.92 | 1.0000 | 0.750,0.520,0.089,0.017 | 0.303,0.448,0.053,0.012 | ❌ |
| statement_date | - | 2026-09-01 | 2026-09-01 | 0.89 | 0.9900 | 0.719,0.081,0.125,0.011 | 0.720,0.081,0.125,0.011 | 🟡 |
