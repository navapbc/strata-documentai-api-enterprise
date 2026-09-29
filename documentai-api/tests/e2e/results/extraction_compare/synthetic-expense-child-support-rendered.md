# synthetic-expense-child-support-rendered.pdf


_Run: 2026-09-29 19:57 UTC_


## Durations

- bda: 27.89s extraction
- ocr-mapping: 1.826s extraction


## Cost

_By Service_
- us.amazon.nova-pro-v1:0: $0.01369680 (15209 in / 478 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05369680**

_By Extraction Method_
- shared (preclassification): $0.00879200
- ocr-mapping extraction: $0.00490480
- primary (bda): $0.04000000
- **total: $0.05369680**


## Accuracy
- BDA: 100% equivalent, 100% close, 0% misses
- OCR Mapping: 83% equivalent, 83% close, 17% misses


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| case_number | FC-2026-047532 | ✅ FC-2026-047532 | ✅ FC-2026-047532 | 0.93 | 1.0000 | 0.674,0.121,0.164,0.013 | 0.575,0.121,0.263,0.013 | ❌ |
| child_name | - | - | - | 0.94 | - | - | - |  |
| court_name | Fourth Judicial District Court, Missoula County | ✅ Fourth Judicial District Court, Missoula County | ✅ Fourth Judicial District Court, Missoula County | 0.78 | 1.0000 | 0.374,0.414,0.376,0.014 | 0.375,0.414,0.376,0.014 | 🟡 |
| effective_end_date | - | - | - | 0.02 | - | - | - |  |
| effective_start_date | - | - | - | 0.03 | - | 0.461,0.644,0.061,0.013 | - | ❌ |
| order_date | - | - | ❌ 2026-09-01 | 0.83 | 1.0000 | - | 0.190,0.120,0.186,0.017 | ❌ |
| payer_name | Jordan Rivera | ✅ Jordan Rivera | ✅ Jordan Rivera | 0.91 | 1.0000 | 0.325,0.252,0.114,0.011 | 0.325,0.252,0.113,0.012 | 🟡 |
| payment_amount | 800 | ✅ 800 | ✅ 800 | 0.93 | 1.0000 | 0.374,0.438,0.040,0.014 | 0.374,0.438,0.249,0.015 | ❌ |
| payment_frequency | Weekly | ✅ Weekly | ✅ Weekly | 0.91 | 1.0000 | 0.373,0.464,0.145,0.015 | 0.373,0.464,0.212,0.015 | ❌ |
| payment_type | Child Support | ✅ Child Support | ❌ - | 0.43 | - | 0.258,0.071,0.160,0.020 | - | ❌ |
| recipient_address | - | - | - | 0.55 | - | - | - |  |
| recipient_name.first_name | - | - | - | 0.89 | - | - | - |  |
| recipient_name.last_name | - | - | - | 0.35 | - | - | - |  |
| recipient_name.middle_name | - | - | - | 0.88 | - | - | - |  |
| recipient_state | - | - | - | 0.14 | - | - | - |  |
| recipient_zip_code | - | - | - | 0.16 | - | - | - |  |
