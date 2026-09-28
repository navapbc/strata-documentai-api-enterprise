# synthetic-insurance-health-insurance-premium-render.pdf


_Run: 2026-09-28 18:37 UTC_


## Durations

- bda: 23.43s extraction
- llm: 2.921s extraction


## Cost

_By Service_
- us.amazon.nova-pro-v1:0: $0.01338960 (14225 in / 628 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05338960**

_By Extraction Method_
- shared (preclassification): $0.00881440
- llm extraction: $0.00457520
- primary (bda): $0.04000000
- **total: $0.05338960**


## Accuracy
- BDA: 100% exact, 100% loose, 0% misses
- LLM: 82% exact, 82% loose, 18% misses


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| coverage_end_date | 2026-08-31 | ✅ 2026-08-31 | ✅ 2026-08-31 | 0.84 | 1.0000 | 0.698,0.246,0.115,0.013 | 0.697,0.246,0.115,0.013 | 🟡 |
| coverage_start_date | 2026-08-01 | ✅ 2026-08-01 | ✅ 2026-08-01 | 0.84 | 0.9300 | 0.698,0.229,0.106,0.013 | 0.697,0.229,0.107,0.013 | 🟡 |
| employer_name | - | - | - | 0.94 | - | - | - |  |
| insurer_or_marketplace_name | Clearview Insurance Services | ✅ Clearview Insurance Services | ✅ Clearview Insurance Services | 0.89 | 1.0000 | 0.128,0.058,0.309,0.031 | 0.110,0.184,0.218,0.011 | ❌ |
| payment_due_date | 2026-09-20 | ✅ 2026-09-20 | ✅ 2026-09-20 | 0.92 | 1.0000 | 0.698,0.277,0.084,0.010 | 0.698,0.277,0.083,0.010 | 🟡 |
| payment_frequency | Monthly | ✅ Monthly | ✅ Monthly | 0.88 | 1.0000 | 0.788,0.513,0.057,0.013 | 0.789,0.513,0.057,0.013 | 🟡 |
| payment_status | Paid | ✅ Paid | ✅ Paid | 0.82 | N/A | - | 0.128,0.796,0.130,0.010 | ❌ |
| policy_or_member_id | CLV-98274651 | ✅ CLV-98274651 | ✅ CLV-98274651 | 0.94 | 1.0000 | 0.250,0.451,0.103,0.011 | 0.250,0.451,0.103,0.011 | ✅ |
| policyholder_name | Jordan Rivera | ✅ Jordan Rivera | ✅ Jordan Rivera | 0.93 | 1.0000 | 0.249,0.366,0.098,0.010 | 0.249,0.366,0.097,0.010 | 🟡 |
| premium_amount | 390 | ✅ 390 | ❌ 600.00 | 0.95 | 1.0000 | 0.782,0.474,0.064,0.013 | 0.787,0.386,0.058,0.012 | ❌ |
| statement_date | 2026-09-05 | ✅ 2026-09-05 | ✅ 2026-09-05 | 0.92 | 1.0000 | 0.698,0.197,0.084,0.011 | 0.697,0.198,0.084,0.010 | 🟡 |
| subsidy_or_tax_credit_amount | 240 | ✅ 240 | ❌ -240.00 | 0.81 | 1.0000 | 0.783,0.414,0.063,0.012 | 0.783,0.415,0.063,0.012 | 🟡 |
