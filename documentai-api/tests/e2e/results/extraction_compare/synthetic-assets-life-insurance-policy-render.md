_Run: 2026-09-25 16:54 UTC_


## synthetic-assets-life-insurance-policy-render.pdf

**Durations**

- bda: 20.25s extraction
- llm: 1.465s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| cash_surrender_value | - | 9500 | 9500 | 0.71 | 1.0000 | 0.477,0.474,0.059,0.015 | 0.477,0.473,0.059,0.015 | 🟡 |
| death_benefit | - | 100000 | 100000 | 0.91 | 1.0000 | 0.477,0.438,0.080,0.015 | 0.477,0.438,0.080,0.015 | ✅ |
| insured_name | - | Jordan Rivera | Jordan Rivera | 0.92 | 1.0000 | 0.476,0.368,0.125,0.015 | 0.476,0.333,0.125,0.015 | ❌ |
| insurer_name | - | Northstar Life Insurance | Northstar Life Insurance Company | 0.41 | 1.0000 | 0.274,0.034,0.224,0.030 | 0.148,0.774,0.309,0.016 | ❌ |
| policy_number | - | XX-1234567-MD | XX-1234567-MD | 0.93 | 1.0000 | 0.477,0.262,0.145,0.012 | 0.477,0.262,0.145,0.012 | ✅ |
| policy_type | - | Universal Life Insurance | Universal Life Insurance | 0.89 | 1.0000 | 0.477,0.403,0.225,0.013 | 0.477,0.403,0.225,0.013 | ✅ |
| policyholder_name | - | Jordan Rivera | Jordan Rivera | 0.93 | 1.0000 | 0.476,0.333,0.125,0.015 | 0.476,0.333,0.125,0.015 | ✅ |
| premium_amount | - | 50 | 50.00 | 0.91 | 1.0000 | 0.477,0.508,0.059,0.014 | 0.477,0.508,0.059,0.014 | ✅ |
| premium_frequency | - | Monthly | Monthly | 0.71 | N/A | 0.542,0.508,0.089,0.016 | - | ❌ |
| statement_date | - | 2026-08-31 | 2026-08-31 | 0.82 | 1.0000 | 0.477,0.297,0.138,0.016 | 0.477,0.297,0.139,0.016 | 🟡 |
