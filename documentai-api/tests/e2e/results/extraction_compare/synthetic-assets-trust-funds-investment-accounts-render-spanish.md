# synthetic-assets-trust-funds-investment-accounts-render-spanish.png


_Run: 2026-09-30 16:51 UTC_


## Durations

- bda: 23.9s extraction
- ocr-mapping: 2.246s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384
- us.amazon.nova-pro-v1:0: $0.01392960
- bda: $0.04000000
- **total: $0.05405344**

_By Extraction Method_
- shared (preclassification): $0.00932064
- ocr-mapping extraction: $0.00473280
- primary (bda): $0.04000000
- **total: $0.05405344**


## Accuracy

_By Extracted Data_
- BDA: 80% equivalent, 90% close, 10% misses
- OCR Mapping: 80% equivalent, 90% close, 10% misses

_By Geometry_
- BDA: 1/6 exact, 5 miss
- OCR Mapping: 2/6 exact, 4 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Geo | BDA Geometry | LLM Geometry |
|---|---|---|---|---|---|---|---|---|
| account_balance | 45000.00 | ✅ 45000 | ✅ 45000.00 | 0.94 | 1.0000 | - | 0.866,0.327,0.083,0.011 | 0.866,0.327,0.083,0.011 |
| account_number | PTC-9***-4582 | ✅ PTC-9***-4582 | ✅ PTC-9***-4582 | 0.52 | 0.9700 | 0.258,0.285,0.104,0.008 | ✅ 0.258,0.284,0.104,0.009 | ✅ 0.258,0.284,0.104,0.009 |
| asset_types | Acciones (Nacionales), Bonos (Renta Fija), Fondos Mutuos, Efectivo y Equivalentes | ❌ - | ✅ Acciones (Nacionales), Bonos (Renta Fija), Fondos Mutuos, Efectivo y Equivalentes | - | N/A | - | - | 0.041,0.815,0.156,0.011 |
| beneficiary_name | María Isabel Rivera | ✅ María Isabel Rivera | ✅ María Isabel Rivera | 0.73 | 0.9500 | 0.041,0.179,0.348,0.023 | ❌ 0.258,0.187,0.131,0.009 | ❌ 0.258,0.187,0.131,0.009 |
| distributions_during_period | 900.00 | ✅ 900 | ❌ (900.00) | 0.95 | 1.0000 | 0.548,0.557,0.050,0.009 | ❌ 0.889,0.270,0.061,0.010 | ❌ 0.889,0.270,0.061,0.010 |
| statement_period_end | 2026-08-31 | ✅ 2026-08-31 | ✅ 2026-08-31 | 0.71 | 1.0000 | - | 0.790,0.148,0.062,0.008 | 0.746,0.148,0.168,0.008 |
| statement_period_start | 2026-06-01 | ✅ 2026-06-01 | ✅ 2026-06-01 | 0.85 | 0.9900 | - | 0.271,0.410,0.121,0.010 | 0.271,0.410,0.284,0.010 |
| trust_name | Fideicomiso Rivera 2019 | 🟡 Fideicomiso Rivera 2019 R | 🟡 Fideicomiso Rivera 2019 R | 0.92 | 0.8600 | 0.041,0.147,0.873,0.009 | ❌ 0.258,0.147,0.175,0.008 | ❌ 0.258,0.147,0.175,0.008 |
| trust_type | Revocable (Inter Vivos) | ✅ Revocable (Inter Vivos) | ✅ Revocable (Inter Vivos) | 0.93 | 0.9500 | 0.040,0.167,0.586,0.010 | ❌ 0.258,0.167,0.153,0.010 | ❌ 0.258,0.167,0.153,0.010 |
| trustee_name | Pinehurst Trust Company | ✅ Pinehurst Trust Company | ✅ Pinehurst Trust Company | 0.91 | 1.0000 | 0.738,0.023,0.170,0.010 | ❌ 0.258,0.264,0.174,0.010 | ✅ 0.738,0.023,0.171,0.010 |
