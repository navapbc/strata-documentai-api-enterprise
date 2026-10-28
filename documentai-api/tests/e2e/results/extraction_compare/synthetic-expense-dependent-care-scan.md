# synthetic-expense-dependent-care-scan.png


_Run: 2026-10-01 02:38 UTC_


## Durations

- bda: 25.71s extraction
- ocr-mapping: 2.132s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384
- us.amazon.nova-pro-v1:0: $0.01400320
- bda: $0.04000000
- **total: $0.05412704**

_By Extraction Method_
- shared (preclassification): $0.00926944
- ocr-mapping extraction: $0.00485760
- primary (bda): $0.04000000
- **total: $0.05412704**


## Accuracy

_By Extracted Data_
- BDA: 9/11 (82%) equivalent match, 9/11 (82%) close, 2 misses
- OCR Mapping: 11/11 (100%) equivalent match, 11/11 (100%) close, 0 misses

_By Bounding Box_
- BDA: 2/3 exact, 1 miss
- OCR Mapping: 1/3 exact, 2 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Bounding Box | BDA Bounding Box | LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| amount_paid | 650.00 | ✅ 650 | ✅ 650.00 | 0.80 | 1.0000 | - | 0.860,0.658,0.061,0.011 | 0.602,0.718,0.142,0.010 |
| balance_due | 650.00 | ✅ 650 | ✅ 650.00 | 0.94 | 1.0000 | - | 0.868,0.743,0.065,0.012 | 0.603,0.744,0.115,0.010 |
| dependent_names | Elliot James Morgan | ❌ - | ✅ Elliot James Morgan | - | N/A | 0.064,0.342,0.153,0.012 | ❌ - | ❌ 0.064,0.318,0.288,0.010 |
| document_type | Dependent Care Expense Statement | ✅ DEPENDENT CARE EXPENSE STATEMENT | ✅ DEPENDENT CARE EXPENSE STATEMENT | 0.87 | 1.0000 | - | 0.655,0.046,0.261,0.035 | 0.647,0.242,0.217,0.011 |
| payment_amount | 325.00 | ✅ 325 | ✅ 325.00 | 0.78 | N/A | - | 0.722,0.466,0.061,0.011 | 0.733,0.444,0.040,0.009 |
| payment_frequency | Weekly | ❌ - | ✅ Weekly | 0.81 | 0.9900 | - | - | 0.064,0.375,0.229,0.013 |
| provider_address | 321 Whispering Pines Drive Holly Springs, NC 27540 | ✅ 321 Whispering Pines Drive Holly Springs, NC 27540 | ✅ 321 Whispering Pines Drive, Holly Springs, NC 27540 | 0.91 | N/A | - | 0.219,0.071,0.207,0.029 | 0.219,0.049,0.337,0.015 |
| provider_name | Pine Ridge Family Learning Center | ✅ Pine Ridge Family Learning Center | ✅ Pine Ridge Family Learning Center | 0.93 | 1.0000 | 0.220,0.049,0.335,0.014 | ✅ 0.219,0.049,0.336,0.015 | ✅ 0.219,0.049,0.337,0.015 |
| service_end_date | 2026-08-30 | ✅ 2026-08-30 | ✅ 2026-08-30 | 0.77 | 0.9100 | - | 0.859,0.123,0.082,0.009 | 0.607,0.123,0.334,0.009 |
| service_start_date | 2026-08-03 | ✅ 2026-08-03 | ✅ 2026-08-03 | 0.79 | 0.9100 | - | 0.758,0.123,0.090,0.010 | 0.607,0.123,0.334,0.009 |
| statement_date | 2026-09-02 | ✅ 2026-09-02 | ✅ 2026-09-02 | 0.83 | 1.0000 | 0.758,0.104,0.081,0.009 | ✅ 0.757,0.103,0.083,0.009 | ❌ 0.607,0.103,0.233,0.009 |
