# synthetic-expense-child-support-spanish-picture.png


_Run: 2026-09-29 19:57 UTC_


## Durations

- bda: 31.8s extraction
- ocr-mapping: 2.57s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384 (1956 in / 27 out)
- us.amazon.nova-pro-v1:0: $0.01563120 (16791 in / 687 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05575504**

_By Extraction Method_
- shared (preclassification): $0.00931744
- ocr-mapping extraction: $0.00643760
- primary (bda): $0.04000000
- **total: $0.05575504**


## Accuracy
- BDA: 77% equivalent, 77% close, 23% misses
- OCR Mapping: 92% equivalent, 92% close, 8% misses


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| case_number | CS-21-123456 | ✅ CS-21-123456 | ✅ CS-21-123456 | 0.90 | 0.9600 | 0.476,0.248,0.087,0.008 | 0.476,0.248,0.087,0.008 | ✅ |
| child_name | - | - | - | 0.88 | - | - | - |  |
| court_name | Tribunal de Familia de la Ciudad de Norfolk | ✅ Tribunal de Familia de la Ciudad de Norfolk | ✅ Tribunal de Familia de la Ciudad de Norfolk | 0.86 | 0.9900 | 0.366,0.264,0.236,0.021 | 0.366,0.277,0.147,0.008 | ❌ |
| effective_end_date | - | - | - | 0.88 | - | - | - |  |
| effective_start_date | 2021-01-05 | ❌ 2021-05-01 | ✅ 2021-01-05 | 0.84 | 0.9900 | 0.171,0.385,0.072,0.009 | 0.485,0.293,0.069,0.008 | ❌ |
| order_date | 2021-01-05 | ❌ 2021-05-01 | ✅ 2021-01-05 | 0.84 | 0.9900 | 0.485,0.293,0.069,0.009 | 0.485,0.293,0.069,0.008 | 🟡 |
| payer_name | Daniel Ortega | ✅ Daniel Ortega | ✅ Daniel Ortega | 0.88 | 1.0000 | 0.646,0.251,0.089,0.010 | 0.647,0.251,0.089,0.010 | 🟡 |
| payment_amount | 450.00 | ✅ 450 | ✅ 450.00 | 0.73 | 1.0000 | 0.241,0.352,0.077,0.010 | 0.241,0.353,0.052,0.009 | ❌ |
| payment_frequency | Semanal | ✅ Semanal | ❌ Weekly | 0.91 | 1.0000 | 0.208,0.369,0.054,0.008 | 0.208,0.369,0.054,0.008 | ✅ |
| payment_type | Child Support | ❌ - | ✅ Child Support | 0.05 | 0.9900 | - | 0.366,0.232,0.181,0.008 | ❌ |
| recipient_address | 4721 Willow Crossing Drive Apt. 3B, Norfolk, VA 23513 | ✅ 4721 Willow Crossing Drive, Apt. 3B Norfolk, VA 23513 | ✅ 4721 Willow Crossing Drive, Apt. 3B, Norfolk, VA 23513 | 0.83 | 1.0000 | 0.074,0.262,0.220,0.023 | 0.074,0.263,0.220,0.010 | ❌ |
| recipient_name.first_name | Marisol | ✅ Marisol | ✅ Marisol | 0.89 | 1.0000 | 0.076,0.248,0.048,0.008 | 0.076,0.248,0.048,0.008 | ✅ |
| recipient_name.last_name | Vega | ✅ Vega | ✅ Vega | 0.84 | 1.0000 | 0.128,0.248,0.033,0.009 | 0.129,0.248,0.033,0.009 | 🟡 |
| recipient_name.middle_name | - | - | - | 0.84 | - | - | - |  |
| recipient_state | VA | ✅ VA | ✅ VA | 0.88 | 1.0000 | 0.127,0.276,0.017,0.008 | 0.249,0.148,0.017,0.007 | ❌ |
| recipient_zip_code | 23513 | ✅ 23513 | ✅ 23513 | 0.89 | 1.0000 | 0.149,0.276,0.039,0.008 | 0.148,0.276,0.039,0.008 | 🟡 |
