_Run: 2026-09-25 16:54 UTC_


## synthetic-assets-trust-funds-investment-accounts-render-spanish.png

**Durations**

- bda: 21.52s extraction
- llm: 2.68s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_balance | - | 45000 | 45000.00 | 0.94 | 1.0000 | 0.866,0.327,0.083,0.011 | 0.866,0.327,0.083,0.011 | ✅ |
| account_number | - | PTC-9***-4582 | PTC-9***-4582 | 0.52 | 0.9700 | 0.258,0.284,0.104,0.009 | 0.258,0.284,0.104,0.009 | ✅ |
| asset_types | - | - | Acciones (Nacionales), Bonos (Renta Fija), Fondos Mutuos, Efectivo y Equivalentes | - | N/A | - | 0.041,0.815,0.156,0.011 | ❌ |
| beneficiary_name | - | María Isabel Rivera | María Isabel Rivera | 0.73 | 0.9500 | 0.258,0.187,0.131,0.009 | 0.258,0.187,0.131,0.009 | ✅ |
| distributions_during_period | - | 900 | (900.00) | 0.95 | 1.0000 | 0.889,0.270,0.061,0.010 | 0.889,0.270,0.061,0.010 | ✅ |
| statement_period_end | - | 2026-08-31 | 2026-08-31 | 0.72 | 1.0000 | 0.790,0.148,0.062,0.008 | 0.746,0.148,0.168,0.008 | ❌ |
| statement_period_start | - | 2026-06-01 | 2026-06-01 | 0.85 | 0.9900 | 0.271,0.410,0.121,0.010 | 0.271,0.410,0.284,0.010 | ❌ |
| trust_name | - | Fideicomiso Rivera 2019 R | Fideicomiso Rivera 2019 R | 0.93 | 0.8600 | 0.258,0.147,0.175,0.008 | 0.258,0.147,0.175,0.008 | ✅ |
| trust_type | - | Revocable (Inter Vivos) | Revocable (Inter Vivos) | 0.93 | 0.9500 | 0.258,0.167,0.153,0.010 | 0.258,0.167,0.153,0.010 | ✅ |
| trustee_name | - | Pinehurst Trust Company | Pinehurst Trust Company | 0.91 | 1.0000 | 0.258,0.264,0.174,0.010 | 0.738,0.023,0.171,0.010 | ❌ |
