# synthetic-assets-bank-statement-render.pdf


_Run: 2026-09-30 02:19 UTC_


## Durations

- bda: 22.38s extraction
- ocr-mapping: 1.86s extraction


## Cost

_By Service_
- us.amazon.nova-pro-v1:0: $0.01378080
- bda: $0.04000000
- **total: $0.05378080**

_By Extraction Method_
- shared (preclassification): $0.00876640
- ocr-mapping extraction: $0.00501440
- primary (bda): $0.04000000
- **total: $0.05378080**


## Accuracy

_By Extracted Data_
- BDA: 75% equivalent, 75% close, 25% misses
- OCR Mapping: 100% equivalent, 100% close, 0% misses

_By Geometry_
- BDA: 4/4 exact, 0 miss
- OCR Mapping: 4/4 exact, 0 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Geo | BDA Geometry | LLM Geometry |
|---|---|---|---|---|---|---|---|---|
| account_holder_address | 7429 Oak Crest Drive, Little Rock, AR 72205 | ✅ 7429 Oak Crest Drive, Little Rock, AR 72205 | ✅ 7429 Oak Crest Drive, Little Rock, AR 72205 | 0.89 | 1.0000 | - | 0.123,0.330,0.383,0.014 | 0.123,0.330,0.383,0.012 |
| account_holder_name | Elias K. Thornton | ✅ Elias K. Thornton | ✅ Elias K. Thornton | 0.93 | 1.0000 | 0.124,0.307,0.150,0.011 | ✅ 0.124,0.306,0.151,0.013 | ✅ 0.124,0.306,0.151,0.013 |
| account_number | ****5678 | ✅ ****5678 | ✅ ****5678 | 0.81 | 1.0000 | 0.269,0.207,0.069,0.011 | ✅ 0.269,0.207,0.070,0.011 | ✅ 0.268,0.207,0.071,0.011 |
| account_summary.summary_amount | 2275.00, 4220.00, 3460.40, 0.00, 3034.60 | ❌ - | ✅ 2275.00, 4220.00, 3460.40, 0.00, 3034.60 | - | N/A | - | - | 0.738,0.591,0.091,0.015 |
| account_summary.summary_desc | Beginning Balance, Total Deposits / Credits, Total Withdrawals / Debits, Fees, Ending Balance | ❌ - | ✅ Beginning Balance, Total Deposits / Credits, Total Withdrawals / Debits, Fees, Ending Balance | - | N/A | - | - | 0.135,0.474,0.137,0.015 |
| account_type | - | - | - | 0.91 | - | - | - | - |
| bank_name | Riverbend Financial Institution | ✅ Riverbend Financial Institution | ✅ Riverbend Financial Institution | 0.92 | 1.0000 | - | 0.228,0.045,0.212,0.049 | 0.229,0.079,0.211,0.015 |
| branch_transit_number | - | - | - | 0.93 | - | - | - | - |
| statement_end_date | 2026-08-31 | ✅ 08/31/2026 | ✅ 2026-08-31 | 0.75 | 1.0000 | 0.406,0.177,0.087,0.011 | ✅ 0.405,0.177,0.089,0.011 | ✅ 0.406,0.177,0.089,0.011 |
| statement_start_date | 2026-06-01 | ✅ 06/01/2026 | ✅ 2026-06-01 | 0.80 | 1.0000 | 0.292,0.177,0.087,0.011 | ✅ 0.291,0.177,0.088,0.011 | ✅ 0.291,0.177,0.088,0.011 |
