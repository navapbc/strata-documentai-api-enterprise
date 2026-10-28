# synthetic-expense-dependent-care-render.pdf


_Run: 2026-10-01 02:38 UTC_


## Durations

- bda: 25.53s extraction
- ocr-mapping: 1.76s extraction


## Cost

_By Service_
- us.amazon.nova-pro-v1:0: $0.01299920
- bda: $0.04000000
- **total: $0.05299920**

_By Extraction Method_
- shared (preclassification): $0.00883360
- ocr-mapping extraction: $0.00416560
- primary (bda): $0.04000000
- **total: $0.05299920**


## Accuracy

_By Extracted Data_
- BDA: 10/11 (91%) equivalent match, 10/11 (91%) close, 1 miss
- OCR Mapping: 11/11 (100%) equivalent match, 11/11 (100%) close, 0 misses

_By Bounding Box_
- BDA: 3/7 exact, 3 miss
- OCR Mapping: 5/7 exact, 2 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Bounding Box | BDA Bounding Box | LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| amount_paid | 1000.00 | ✅ 1000 | ✅ 1000.00 | 0.95 | 1.0000 | - | 0.733,0.782,0.085,0.015 | 0.733,0.783,0.085,0.014 |
| balance_due | 1000.00 | ✅ 1000 | ✅ 1000.00 | 0.95 | 1.0000 | - | 0.733,0.820,0.085,0.015 | 0.733,0.783,0.085,0.014 |
| dependent_names | Elliot Morgan | ❌ - | ✅ Elliot Morgan | - | 1.0000 | 0.195,0.360,0.105,0.014 | ❌ - | ✅ 0.195,0.361,0.105,0.014 |
| document_type | Dependent Care Expense Statement | ✅ Dependent Care Expense Statement | ✅ Dependent Care Expense Statement | 0.84 | 1.0000 | 0.213,0.179,0.561,0.025 | 🟡 0.213,0.179,0.250,0.026 | ✅ 0.213,0.179,0.562,0.026 |
| payment_amount | 2000.00 | ✅ 2000 | ✅ 2000.00 | 0.25 | 1.0000 | 0.734,0.746,0.084,0.015 | ✅ 0.733,0.745,0.085,0.015 | ✅ 0.733,0.745,0.085,0.015 |
| payment_frequency | Weekly | ✅ Weekly | ✅ Weekly | 0.92 | 1.0000 | 0.512,0.446,0.056,0.014 | ✅ 0.512,0.445,0.057,0.014 | ✅ 0.512,0.445,0.057,0.014 |
| provider_address | 485 Maple Avenue, Providence, RI 02903 | ✅ 485 Maple Avenue, Providence, RI 02903 | ✅ 485 Maple Avenue, Providence, RI 02903 | 0.91 | 1.0000 | 0.101,0.081,0.456,0.028 | ❌ 0.249,0.090,0.308,0.014 | ❌ 0.249,0.090,0.308,0.014 |
| provider_name | Bright Horizons Early Learning Center | ✅ Bright Horizons Early Learning Center | ✅ Bright Horizons Early Learning Center | 0.89 | 1.0000 | 0.115,0.053,0.735,0.023 | ❌ 0.213,0.053,0.425,0.019 | ❌ 0.213,0.053,0.425,0.019 |
| service_end_date | 2026-08-30 | ✅ 2026-08-30 | ✅ 2026-08-30 | 0.77 | 1.0000 | - | 0.617,0.650,0.074,0.013 | 0.194,0.446,0.103,0.014 |
| service_start_date | 2026-08-03 | ✅ 2026-08-03 | ✅ 2026-08-03 | 0.64 | 1.0000 | - | 0.194,0.446,0.103,0.014 | 0.194,0.446,0.103,0.014 |
| statement_date | 2026-09-05 | ✅ 2026-09-05 | ✅ 2026-09-05 | 0.91 | 1.0000 | 0.721,0.076,0.092,0.011 | ✅ 0.720,0.076,0.094,0.012 | ✅ 0.720,0.076,0.094,0.012 |
