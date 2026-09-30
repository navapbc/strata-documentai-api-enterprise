# synthetic-insurance-health-insurance-premium-render.pdf


_Run: 2026-09-30 02:19 UTC_


## Durations

- bda: 26.43s extraction
- ocr-mapping: 2.186s extraction


## Cost

_By Service_
- us.amazon.nova-pro-v1:0: $0.01343360
- bda: $0.04000000
- **total: $0.05343360**

_By Extraction Method_
- shared (preclassification): $0.00877600
- ocr-mapping extraction: $0.00465760
- primary (bda): $0.04000000
- **total: $0.05343360**


## Accuracy

_By Extracted Data_
- BDA: 100% equivalent, 100% close, 0% misses
- OCR Mapping: 91% equivalent, 91% close, 9% misses

_By Geometry_
- BDA: 4/5 exact, 1 miss
- OCR Mapping: 5/5 exact, 0 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Geo | BDA Geometry | LLM Geometry |
|---|---|---|---|---|---|---|---|---|
| coverage_end_date | 2026-08-31 | ✅ 2026-08-31 | ✅ 2026-08-31 | 0.84 | 1.0000 | - | 0.698,0.246,0.115,0.013 | 0.697,0.246,0.115,0.013 |
| coverage_start_date | 2026-08-01 | ✅ 2026-08-01 | ✅ 2026-08-01 | 0.84 | 0.9300 | - | 0.698,0.229,0.106,0.013 | 0.697,0.229,0.107,0.013 |
| employer_name | - | - | - | 0.94 | N/A | - | - | - |
| insurer_or_marketplace_name | Clearview Insurance Services | ✅ Clearview Insurance Services | ✅ Clearview Insurance Services | 0.89 | 1.0000 | 0.110,0.184,0.217,0.010 | ❌ 0.128,0.058,0.309,0.031 | ✅ 0.110,0.184,0.218,0.011 |
| payment_due_date | 2026-09-20 | ✅ 2026-09-20 | ✅ 2026-09-20 | 0.93 | 1.0000 | 0.698,0.277,0.083,0.009 | ✅ 0.698,0.277,0.084,0.010 | ✅ 0.698,0.277,0.083,0.010 |
| payment_frequency | Monthly | ✅ Monthly | ✅ Monthly | 0.88 | 1.0000 | 0.789,0.511,0.056,0.018 | ✅ 0.788,0.513,0.057,0.013 | ✅ 0.789,0.513,0.057,0.013 |
| payment_status | Paid | ✅ Paid | ✅ Paid | 0.81 | N/A | - | - | - |
| policy_or_member_id | CLV-98274651 | ✅ CLV-98274651 | ✅ CLV-98274651 | 0.94 | 1.0000 | 0.250,0.451,0.102,0.010 | ✅ 0.250,0.451,0.103,0.011 | ✅ 0.250,0.451,0.103,0.011 |
| policyholder_name | Jordan Rivera | ✅ Jordan Rivera | ✅ Jordan Rivera | 0.93 | 1.0000 | - | 0.249,0.366,0.098,0.010 | 0.249,0.366,0.097,0.010 |
| premium_amount | 390.00 | ✅ 390 | ✅ 390.00 | 0.95 | 1.0000 | - | 0.782,0.474,0.064,0.013 | 0.782,0.474,0.063,0.013 |
| statement_date | 2026-09-05 | ✅ 2026-09-05 | ✅ 2026-09-05 | 0.92 | 1.0000 | 0.698,0.198,0.083,0.010 | ✅ 0.698,0.197,0.084,0.011 | ✅ 0.697,0.198,0.084,0.010 |
| subsidy_or_tax_credit_amount | 240.00 | ✅ 240 | ❌ -240.00 | 0.82 | 1.0000 | - | 0.783,0.414,0.063,0.012 | 0.783,0.415,0.063,0.012 |
