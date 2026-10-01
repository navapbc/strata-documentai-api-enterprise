# synthetic-expense-child-support-rendered.pdf


_Run: 2026-09-30 19:07 UTC_


## Durations

- bda: 26.3s extraction
- ocr-mapping: 2.737s extraction


## Cost

_By Service_
- us.amazon.nova-pro-v1:0: $0.01453840
- bda: $0.04000000
- **total: $0.05453840**

_By Extraction Method_
- shared (preclassification): $0.00877600
- ocr-mapping extraction: $0.00576240
- primary (bda): $0.04000000
- **total: $0.05453840**


## Accuracy

_By Extracted Data_
- BDA: 100% equivalent, 100% close, 0% misses
- OCR Mapping: 100% equivalent, 100% close, 0% misses

_By Geometry_
- BDA: 2/6 exact, 4 miss
- OCR Mapping: 0/6 exact, 6 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Geo | BDA Geometry | LLM Geometry |
|---|---|---|---|---|---|---|---|---|
| case_number | FC-2026-047532 | ✅ FC-2026-047532 | ✅ FC-2026-047532 | 0.93 | 1.0000 | 0.674,0.121,0.164,0.013 | ✅ 0.674,0.121,0.164,0.013 | ❌ 0.575,0.121,0.263,0.013 |
| child_name | - | - | - | 0.94 | N/A | - | - | - |
| court_name | Fourth Judicial District Court, Missoula County | ✅ Fourth Judicial District Court, Missoula County | ✅ Fourth Judicial District Court, Missoula County | 0.78 | 1.0000 | 0.123,0.414,0.628,0.015 | ❌ 0.374,0.414,0.376,0.014 | ❌ 0.375,0.414,0.376,0.014 |
| effective_end_date | - | - | ❌ 2026-08-24 | 0.02 | 1.0000 | - | - | 0.480,0.644,0.203,0.014 |
| effective_start_date | - | - | ❌ 2026-07-06 | 0.03 | 1.0000 | - | 0.461,0.644,0.061,0.013 | 0.374,0.644,0.308,0.015 |
| order_date | - | - | ❌ 2026-09-01 | 0.83 | 1.0000 | - | - | 0.190,0.120,0.186,0.017 |
| payer_name | Jordan Rivera | ✅ Jordan Rivera | ✅ Jordan Rivera | 0.91 | 1.0000 | 0.123,0.249,0.315,0.020 | ❌ 0.325,0.252,0.114,0.011 | ❌ 0.325,0.252,0.113,0.012 |
| payment_amount | 800 | ✅ 800 | ✅ 800 | 0.93 | 1.0000 | 0.374,0.439,0.040,0.013 | ✅ 0.374,0.438,0.040,0.014 | ❌ 0.374,0.438,0.249,0.015 |
| payment_frequency | Weekly | ✅ Weekly | ✅ Weekly | 0.91 | 1.0000 | 0.374,0.464,0.058,0.015 | ❌ 0.373,0.464,0.145,0.015 | ❌ 0.373,0.464,0.212,0.015 |
| payment_type | Child Support | ✅ Child Support | ✅ Child Support | 0.42 | 1.0000 | 0.123,0.739,0.499,0.015 | ❌ 0.258,0.071,0.160,0.020 | ❌ 0.123,0.721,0.655,0.015 |
| recipient_address | - | - | ❌ 1523 Aspen Ridge Drive, Helena, MT 59601 | 0.58 | 1.0000 | - | - | 0.326,0.306,0.355,0.015 |
| recipient_name.first_name | - | - | - | 0.89 | N/A | - | - | - |
| recipient_name.last_name | - | - | - | 0.39 | N/A | - | - | - |
| recipient_name.middle_name | - | - | - | 0.88 | N/A | - | - | - |
| recipient_state | - | - | ❌ MT | 0.15 | 1.0000 | - | - | 0.600,0.306,0.027,0.011 |
| recipient_zip_code | - | - | ❌ 59601 | 0.16 | 1.0000 | - | - | 0.633,0.306,0.048,0.011 |
