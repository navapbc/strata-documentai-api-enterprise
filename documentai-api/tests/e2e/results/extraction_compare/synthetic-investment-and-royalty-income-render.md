# synthetic-investment-and-royalty-income-render.pdf


_Run: 2026-10-01 02:38 UTC_


## Durations

- bda: 21.36s extraction
- ocr-mapping: 2.435s extraction


## Cost

_By Service_
- us.amazon.nova-pro-v1:0: $0.01232000
- bda: $0.04000000
- **total: $0.05232000**

_By Extraction Method_
- shared (preclassification): $0.00878880
- ocr-mapping extraction: $0.00353120
- primary (bda): $0.04000000
- **total: $0.05232000**


## Accuracy

_By Extracted Data_
- BDA: 2/6 (33%) equivalent match, 2/6 (33%) close, 4 misses
- OCR Mapping: 6/6 (100%) equivalent match, 6/6 (100%) close, 0 misses

_By Bounding Box_
- BDA: 0/6 exact, 5 miss
- OCR Mapping: 0/6 exact, 5 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Bounding Box | BDA Bounding Box | LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| account_balance | $49,000.00 | ❌ - | ✅ 49000.00 | - | 1.0000 | 0.779,0.684,0.087,0.013 | ❌ - | ❌ 0.130,0.684,0.267,0.014 |
| account_holder_name | Jordan Rivera | ✅ Jordan Rivera | ✅ Jordan Rivera | 0.91 | N/A | 0.117,0.254,0.679,0.016 | 🟡 0.117,0.254,0.112,0.012 | ❌ 0.116,0.228,0.135,0.012 |
| account_number | xxxx-xxxx-1392 | ❌ - | ✅ xxxx-xxxx-1392 | - | 0.9100 | 0.117,0.254,0.679,0.016 | ❌ - | ❌ 0.526,0.259,0.271,0.011 |
| account_type | Traditional IRA | ❌ - | ✅ Traditional IRA | - | 1.0000 | 0.117,0.229,0.673,0.014 | ❌ - | ❌ 0.525,0.229,0.265,0.011 |
| capital_gains_distributions_cumulative | N/A | - | - | 0.91 | - | - | - | - |
| contribution_dates | - | - | ❌ 2025-01-01, 2025-12-31 | - | 1.0000 | - | - | 0.525,0.290,0.260,0.011 |
| distribution_dates | - | - | ❌ 2025-01-01, 2025-12-31 | - | 1.0000 | - | - | 0.525,0.290,0.260,0.011 |
| dividend_payments_cumulative | N/A | - | - | 0.92 | - | - | - | - |
| document_type | N/A | - | - | 0.06 | - | - | - | - |
| financial_institution | Seaport Financial Group | ✅ Seaport Financial Group | ✅ Seaport Financial Group | 0.88 | 0.9800 | 0.114,0.167,0.367,0.011 | ❌ 0.224,0.054,0.191,0.054 | 🟡 0.114,0.166,0.173,0.013 |
| interest_credits_cumulative | N/A | - | - | 0.91 | - | - | - | - |
| statement_period_end | N/A | 2025-12-31 | - | 0.84 | - | - | 0.781,0.309,0.087,0.014 | - |
| statement_period_start | N/A | 2025-01-01 | - | 0.81 | - | - | 0.679,0.308,0.098,0.014 | - |
| tax_year | 2025 | ❌ - | ✅ 2025 | - | 1.0000 | 0.748,0.290,0.037,0.010 | ❌ - | ❌ 0.525,0.290,0.260,0.011 |
| total_value | N/A | 49000 | - | 0.93 | - | - | 0.778,0.683,0.088,0.014 | - |
