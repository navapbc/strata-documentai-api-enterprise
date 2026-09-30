# synthetic-investment-and-royalty-income-render.pdf


_Run: 2026-09-30 02:19 UTC_


## Durations

- bda: 31.51s extraction
- ocr-mapping: 1.88s extraction


## Cost

_By Service_
- us.amazon.nova-pro-v1:0: $0.01231040
- bda: $0.04000000
- **total: $0.05231040**

_By Extraction Method_
- shared (preclassification): $0.00877920
- ocr-mapping extraction: $0.00353120
- primary (bda): $0.04000000
- **total: $0.05231040**


## Accuracy

_By Extracted Data_
- BDA: 100% equivalent, 100% close, 0% misses
- OCR Mapping: 100% equivalent, 100% close, 0% misses

_By Geometry_
- BDA: 1/1 exact, 0 miss
- OCR Mapping: 0/1 exact, 1 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Geo | BDA Geometry | LLM Geometry |
|---|---|---|---|---|---|---|---|---|
| account_balance | $49,000.00 | ✅ $49,000.00 | ✅ 49000.00 | 0.37 | 1.0000 | - | 0.778,0.683,0.088,0.014 | 0.130,0.684,0.267,0.014 |
| account_holder_name | Jordan Rivera | ✅ Jordan Rivera | ✅ Jordan Rivera | 0.91 | N/A | - | 0.117,0.254,0.113,0.012 | 0.116,0.228,0.135,0.012 |
| account_number | xxxx-xxxx-1392 | ✅ xxxx-xxxx-1392 | ✅ xxxx-xxxx-1392 | 0.84 | 0.9100 | - | 0.678,0.260,0.118,0.011 | 0.526,0.259,0.271,0.011 |
| account_type | Traditional IRA | ✅ Traditional IRA | ✅ Traditional IRA | 0.88 | 1.0000 | - | 0.678,0.229,0.112,0.011 | 0.525,0.229,0.265,0.011 |
| contribution_dates | - | - | ❌ 2025-01-01, 2025-12-31 | 0.93 | 1.0000 | - | - | 0.525,0.290,0.260,0.011 |
| distribution_dates | - | - | ❌ 2025-01-01, 2025-12-31 | 0.94 | 1.0000 | - | - | 0.525,0.290,0.260,0.011 |
| financial_institution | Seaport Financial Group | ✅ Seaport Financial Group | ✅ Seaport Financial Group | 0.87 | 0.9800 | - | 0.224,0.054,0.191,0.054 | 0.114,0.166,0.173,0.013 |
| tax_year | 2025 | ✅ 2025 | ✅ 2025 | 0.95 | 1.0000 | 0.748,0.290,0.037,0.010 | ✅ 0.748,0.290,0.038,0.011 | ❌ 0.525,0.290,0.260,0.011 |
