# synthetic-assets-trust-funds-investment-accounts-scan.jpg


_Run: 2026-10-01 02:38 UTC_


## Durations

- bda: 20.94s extraction
- ocr-mapping: 1.98s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012360
- us.amazon.nova-pro-v1:0: $0.01373120
- bda: $0.04000000
- **total: $0.05385480**

_By Extraction Method_
- shared (preclassification): $0.00927880
- ocr-mapping extraction: $0.00457600
- primary (bda): $0.04000000
- **total: $0.05385480**


## Accuracy

_By Extracted Data_
- BDA: 9/10 (90%) equivalent match, 9/10 (90%) close, 1 miss
- OCR Mapping: 9/10 (90%) equivalent match, 10/10 (100%) close, 0 misses

_By Bounding Box_
- BDA: 4/9 exact, 5 miss
- OCR Mapping: 3/9 exact, 6 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Bounding Box | BDA Bounding Box | LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| account_balance | 90000.00 | ✅ 90000 | ✅ 90000.00 | 0.95 | 1.0000 | 0.413,0.497,0.075,0.010 | ✅ 0.414,0.497,0.076,0.011 | ❌ 0.846,0.365,0.084,0.012 |
| account_number | TR-4567-89XX | ✅ TR-4567-89XX | ✅ TR-4567-89XX | 0.94 | 1.0000 | 0.699,0.123,0.097,0.009 | ✅ 0.699,0.123,0.098,0.010 | ✅ 0.700,0.123,0.097,0.010 |
| asset_types | U.S. Equities, Fixed Income, Cash & Cash Equivalents, Alternative Investments | ❌ - | ✅ U.S. Equities, Fixed Income, Cash & Cash Equivalents, Alternative Investments | - | N/A | - | - | 0.053,0.845,0.082,0.009 |
| beneficiary_name | Morgan Elise Dalton | ✅ Morgan Elise Dalton | ✅ Morgan Elise Dalton | 0.93 | 1.0000 | 0.646,0.310,0.132,0.010 | ✅ 0.647,0.310,0.132,0.011 | ❌ 0.046,0.263,0.135,0.011 |
| distributions_during_period | 1800.00 | ✅ 1800 | ✅ 1800.00 | 0.94 | 1.0000 | 0.871,0.396,0.060,0.010 | ❌ 0.418,0.450,0.072,0.011 | ✅ 0.871,0.397,0.060,0.010 |
| statement_period_end | 2026-08-31 | ✅ 2026-08-31 | ✅ 2026-08-31 | 0.85 | 1.0000 | 0.668,0.368,0.066,0.008 | ❌ 0.801,0.105,0.109,0.012 | ❌ 0.699,0.089,0.108,0.012 |
| statement_period_start | 2026-06-01 | ✅ 2026-06-01 | ✅ 2026-06-01 | 0.91 | 1.0000 | 0.056,0.591,0.067,0.007 | ❌ 0.699,0.107,0.089,0.010 | ❌ 0.699,0.105,0.212,0.012 |
| trust_name | The Morgan E. Dalton Revocable Trust | ✅ The Morgan E. Dalton Revocable Trust | ✅ The Morgan E. Dalton Revocable Trust | 0.90 | 1.0000 | 0.646,0.257,0.253,0.010 | ✅ 0.646,0.257,0.255,0.013 | ✅ 0.645,0.257,0.255,0.013 |
| trust_type | Revocable Living Trust | ✅ Revocable Living Trust | ✅ Revocable Living Trust | 0.94 | 1.0000 | 0.646,0.327,0.150,0.010 | ❌ 0.700,0.156,0.151,0.011 | ❌ 0.701,0.156,0.150,0.011 |
| trustee_name | Cedar Grove Trust Company, as Trustee | ✅ Cedar Grove Trust Company, as Trustee | 🟡 Cedar Grove Trust Company | 0.60 | 1.0000 | 0.045,0.289,0.867,0.020 | ❌ 0.268,0.058,0.092,0.018 | ❌ 0.646,0.292,0.193,0.010 |
