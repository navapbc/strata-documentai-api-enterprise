# synthetic-insurance-health-insurance-premium-render.pdf

_Last run: 2026-10-30 03:19 UTC_

## Durations

- bda: 27.32s extraction
- llm: 2.227s extraction

## Cost

_By Service_

- us.amazon.nova-pro-v1:0: $0.01351360 (14396 in / 624 out)
- bda: $0.04000000 (1 page(s))
- analyze_document_layout: $0.00400000 (1 page(s))
- **total: $0.05751360**

_By Extraction Method_

- shared (preclassification): $0.00878240
- ocr-mapping extraction: $0.00873120
- primary (bda): $0.04000000
- **total: $0.05751360**

## Accuracy

_By Extracted Data_

- BDA: 11/11 (100%) equivalent match, 11/11 (100%) close, 0 misses
- OCR Mapping: 11/11 (100%) equivalent match, 11/11 (100%) close, 0 misses

_By Bounding Box_

- BDA: 5/8 (62%) exact, 3 miss
- OCR Mapping: 6/8 (75%) exact, 2 miss

## Field Comparison

| Field | Expected | BDA Value | OCR / LLM Value | BDA Conf | OCR / LLM Conf | Expected Bounding Box | BDA Bounding Box | OCR / LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| coverage_end_date | 2026-08-31 | ✅ 2026-08-31 | ✅ 2026-08-31 | 0.84 | 1.0000 | 0.110,0.236,0.702,0.023 | ❌ 0.697,0.246,0.115,0.013 | ❌ 0.697,0.246,0.115,0.013 |
| coverage_start_date | 2026-08-01 | ✅ 2026-08-01 | ✅ 2026-08-01 | 0.84 | 0.9300 | 0.697,0.229,0.120,0.013 | ✅ 0.697,0.229,0.107,0.013 | ✅ 0.697,0.229,0.107,0.013 |
| employer_name | - | - | - | 0.94 | N/A | - | - | - |
| insurer_or_marketplace_name | Clearview Insurance Services | ✅ Clearview Insurance Services | ✅ Clearview Insurance Services | 0.89 | 1.0000 | 0.110,0.184,0.217,0.010 | ❌ 0.128,0.058,0.309,0.031 | ✅ 0.110,0.184,0.218,0.011 |
| payment_due_date | 2026-09-20 | ✅ 2026-09-20 | ✅ 2026-09-20 | 0.92 | 1.0000 | 0.698,0.277,0.083,0.009 | ✅ 0.698,0.277,0.084,0.010 | ✅ 0.698,0.277,0.083,0.010 |
| payment_frequency | Monthly | ✅ Monthly | ✅ Monthly | 0.88 | 1.0000 | 0.789,0.511,0.056,0.018 | ✅ 0.788,0.513,0.057,0.013 | ✅ 0.789,0.513,0.057,0.013 |
| payment_status | Paid | ✅ Paid | ✅ Paid | 0.81 | N/A | - | - | 0.128,0.823,0.155,0.013 |
| policy_or_member_id | CLV-98274651 | ✅ CLV-98274651 | ✅ CLV-98274651 | 0.94 | 1.0000 | 0.250,0.451,0.102,0.010 | ✅ 0.250,0.451,0.103,0.011 | ✅ 0.250,0.451,0.103,0.011 |
| policyholder_name | Jordan Rivera | ✅ Jordan Rivera | ✅ Jordan Rivera | 0.93 | 1.0000 | 0.107,0.354,0.740,0.021 | ❌ 0.249,0.366,0.097,0.010 | ❌ 0.249,0.366,0.097,0.010 |
| premium_amount | 390.00 | ✅ 390 | ✅ 390.00 | 0.95 | 1.0000 | - | 0.782,0.474,0.064,0.013 | 0.498,0.475,0.097,0.011 |
| statement_date | 2026-09-05 | ✅ 2026-09-05 | ✅ 2026-09-05 | 0.92 | 1.0000 | 0.698,0.198,0.083,0.010 | ✅ 0.698,0.197,0.084,0.011 | ✅ 0.697,0.198,0.084,0.010 |
| subsidy_or_tax_credit_amount | 240.00 | ✅ 240 | ✅ 240.00 | 0.81 | 1.0000 | - | 0.783,0.415,0.063,0.012 | 0.499,0.415,0.115,0.013 |