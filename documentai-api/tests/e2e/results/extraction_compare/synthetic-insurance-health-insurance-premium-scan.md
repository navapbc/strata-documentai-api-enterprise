# synthetic-insurance-health-insurance-premium-scan.jpg


_Run: 2026-10-01 01:41 UTC_


## Durations

- bda: 21.64s extraction
- ocr-mapping: 2.076s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384
- us.amazon.nova-pro-v1:0: $0.01406320
- bda: $0.04000000
- **total: $0.05418704**

_By Extraction Method_
- shared (preclassification): $0.00926944
- ocr-mapping extraction: $0.00491760
- primary (bda): $0.04000000
- **total: $0.05418704**


## Accuracy

_By Extracted Data_
- BDA: 91% equivalent, 100% close, 0% misses
- OCR Mapping: 91% equivalent, 91% close, 9% misses

_By Bounding Box_
- BDA: 4/5 exact, 1 miss
- OCR Mapping: 3/5 exact, 2 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Bounding Box | BDA Bounding Box | LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| coverage_end_date | 2026-09-30 | ✅ 2026-09-30 | ✅ 2026-09-30 | 0.91 | 0.8500 | - | 0.890,0.087,0.081,0.012 | 0.890,0.087,0.081,0.012 |
| coverage_start_date | 2026-09-01 | ✅ 2026-09-01 | ✅ 2026-09-01 | 0.83 | 1.0000 | - | - | 0.791,0.068,0.081,0.011 |
| employer_name | - | - | - | 0.94 | - | - | - | - |
| insurer_or_marketplace_name | Harbor Health Plan, Inc. | 🟡 Harbor Health Plan | ✅ Harbor Health Plan, Inc. | 0.70 | 1.0000 | 0.353,0.039,0.499,0.016 | ❌ 0.135,0.042,0.185,0.044 | ❌ 0.352,0.039,0.111,0.012 |
| payment_due_date | 2026-09-15 | ✅ 2026-09-15 | ✅ 2026-09-15 | 0.92 | 1.0000 | 0.789,0.103,0.081,0.010 | ✅ 0.789,0.103,0.081,0.011 | ✅ 0.789,0.103,0.082,0.011 |
| payment_frequency | Monthly | ✅ monthly | ✅ monthly | 0.86 | 1.0000 | - | 0.080,0.564,0.055,0.012 | 0.047,0.564,0.325,0.014 |
| payment_status | Paid | ✅ Paid | ✅ Paid | 0.88 | 1.0000 | 0.729,0.162,0.057,0.014 | ✅ 0.729,0.162,0.057,0.015 | ❌ 0.729,0.162,0.159,0.016 |
| policy_or_member_id | HHP123456789 | ✅ HHP123456789 | ✅ HHP123456789 | 0.95 | 1.0000 | 0.273,0.322,0.101,0.009 | ✅ 0.273,0.321,0.101,0.010 | ✅ 0.273,0.322,0.101,0.010 |
| policyholder_name | Jordan Rivera | ✅ Jordan Rivera | ✅ Jordan Rivera | 0.94 | 1.0000 | 0.094,0.192,0.103,0.011 | ✅ 0.094,0.192,0.104,0.011 | ✅ 0.094,0.192,0.104,0.012 |
| premium_amount | 636.25 | ✅ 636.25 | ✅ 636.25 | 0.95 | 1.0000 | - | 0.884,0.319,0.063,0.013 | 0.884,0.319,0.062,0.013 |
| statement_date | 2026-09-01 | ✅ 2026-09-01 | ✅ 2026-09-01 | 0.91 | 1.0000 | - | 0.790,0.068,0.082,0.011 | 0.791,0.068,0.081,0.011 |
| subsidy_or_tax_credit_amount | 323.75 | ✅ 323.75 | ❌ -323.75 | 0.95 | 1.0000 | - | 0.884,0.269,0.064,0.013 | 0.883,0.269,0.064,0.012 |
