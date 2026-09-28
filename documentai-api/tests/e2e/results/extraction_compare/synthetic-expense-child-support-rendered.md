# synthetic-expense-child-support-rendered.pdf


_Run: 2026-09-28 18:35 UTC_


## Durations

- bda: 31.01s extraction
- llm: 2.868s extraction


## Cost

_By Service_
- us.amazon.nova-pro-v1:0: $0.01437600 (15038 in / 733 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05437600**

_By Extraction Method_
- shared (preclassification): $0.00882080
- llm extraction: $0.00555520
- primary (bda): $0.04000000
- **total: $0.05437600**


## Accuracy
- BDA: 100% exact, 100% loose, 0% misses
- LLM: 100% exact, 100% loose, 0% misses


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| case_number | FC-2026-047532 | ✅ FC-2026-047532 | ✅ FC-2026-047532 | 0.93 | 1.0000 | 0.673,0.121,0.165,0.013 | 0.575,0.121,0.263,0.013 | ❌ |
| child_name | - | - | - | 0.94 | N/A | - | - |  |
| court_name | Fourth Judicial District Court, Missoula County | ✅ Fourth Judicial District Court, Missoula County | ✅ Fourth Judicial District Court, Missoula County | 0.78 | 1.0000 | 0.374,0.414,0.376,0.014 | 0.375,0.414,0.376,0.014 | 🟡 |
| effective_end_date | - | - | - | 0.02 | N/A | - | - |  |
| effective_start_date | - | - | - | 0.03 | N/A | 0.422,0.644,0.100,0.015 | - | ❌ |
| order_date | - | - | ❌ September 1, 2026 | 0.83 | 1.0000 | - | 0.190,0.120,0.186,0.017 | ❌ |
| payer_name | Jordan Rivera | ✅ Jordan Rivera | ✅ Jordan Rivera | 0.91 | 1.0000 | 0.325,0.252,0.114,0.011 | 0.325,0.252,0.113,0.012 | 🟡 |
| payment_amount | 800 | ✅ 800 | ✅ 800 | 0.93 | 1.0000 | 0.374,0.438,0.040,0.014 | 0.374,0.438,0.249,0.015 | ❌ |
| payment_frequency | Weekly | ✅ Weekly | ✅ Weekly | 0.91 | 1.0000 | 0.373,0.464,0.145,0.015 | 0.373,0.464,0.212,0.015 | ❌ |
| payment_type | Child Support | ✅ Child Support | ✅ Child Support | 0.43 | 1.0000 | 0.258,0.071,0.160,0.020 | 0.258,0.071,0.485,0.020 | ❌ |
| recipient_address | - | - | ❌ 1523 Aspen Ridge Drive, Helena, MT 59601 | 0.52 | 1.0000 | - | 0.326,0.306,0.355,0.015 | ❌ |
| recipient_name.first_name | - | - | - | 0.89 | N/A | - | - |  |
| recipient_name.last_name | - | - | - | 0.42 | N/A | - | - |  |
| recipient_name.middle_name | - | - | - | 0.88 | N/A | - | - |  |
| recipient_state | - | - | ❌ MT | 0.14 | 1.0000 | - | 0.326,0.306,0.355,0.015 | ❌ |
| recipient_zip_code | - | - | ❌ 59601 | 0.16 | 1.0000 | - | 0.326,0.306,0.355,0.015 | ❌ |
