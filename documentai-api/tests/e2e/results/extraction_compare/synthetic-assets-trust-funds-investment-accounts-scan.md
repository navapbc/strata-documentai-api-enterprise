# synthetic-assets-trust-funds-investment-accounts-scan.jpg


_Run: 2026-09-29 19:56 UTC_


## Durations

- bda: 20.18s extraction
- ocr-mapping: 2.143s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012360 (1956 in / 26 out)
- us.amazon.nova-pro-v1:0: $0.01373760 (14904 in / 567 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05386120**

_By Extraction Method_
- shared (preclassification): $0.00927560
- ocr-mapping extraction: $0.00458560
- primary (bda): $0.04000000
- **total: $0.05386120**


## Accuracy
- BDA: 90% equivalent, 90% close, 10% misses
- OCR Mapping: 90% equivalent, 100% close, 0% misses


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_balance | 90000.00 | ✅ 90000 | ✅ 90000.00 | 0.95 | 1.0000 | 0.414,0.497,0.076,0.011 | 0.846,0.365,0.084,0.012 | ❌ |
| account_number | TR-4567-89XX | ✅ TR-4567-89XX | ✅ TR-4567-89XX | 0.94 | 1.0000 | 0.699,0.123,0.098,0.010 | 0.700,0.123,0.097,0.010 | 🟡 |
| asset_types | U.S. Equities, Fixed Income, Cash & Cash Equivalents, Alternative Investments | ❌ - | ✅ U.S. Equities, Fixed Income, Cash & Cash Equivalents, Alternative Investments | - | N/A | - | 0.053,0.845,0.082,0.009 | ❌ |
| beneficiary_name | Morgan Elise Dalton | ✅ Morgan Elise Dalton | ✅ Morgan Elise Dalton | 0.93 | 1.0000 | 0.647,0.310,0.132,0.011 | 0.046,0.263,0.135,0.011 | ❌ |
| distributions_during_period | 1800.00 | ✅ 1800 | ✅ 1800.00 | 0.94 | 1.0000 | 0.418,0.450,0.072,0.011 | 0.871,0.397,0.060,0.010 | ❌ |
| statement_period_end | 2026-08-31 | ✅ 2026-08-31 | ✅ 2026-08-31 | 0.85 | 1.0000 | 0.801,0.105,0.109,0.012 | 0.699,0.089,0.108,0.012 | ❌ |
| statement_period_start | 2026-06-01 | ✅ 2026-06-01 | ✅ 2026-06-01 | 0.91 | 1.0000 | 0.699,0.107,0.089,0.010 | 0.699,0.105,0.212,0.012 | ❌ |
| trust_name | The Morgan E. Dalton Revocable Trust | ✅ The Morgan E. Dalton Revocable Trust | ✅ The Morgan E. Dalton Revocable Trust | 0.90 | 1.0000 | 0.646,0.257,0.255,0.013 | 0.645,0.257,0.255,0.013 | 🟡 |
| trust_type | Revocable Living Trust | ✅ Revocable Living Trust | ✅ Revocable Living Trust | 0.94 | 1.0000 | 0.700,0.156,0.151,0.011 | 0.701,0.156,0.150,0.011 | 🟡 |
| trustee_name | Cedar Grove Trust Company, as Trustee | ✅ Cedar Grove Trust Company, as Trustee | 🟡 Cedar Grove Trust Company | 0.60 | 1.0000 | 0.268,0.058,0.092,0.018 | 0.646,0.291,0.267,0.011 | ❌ |
