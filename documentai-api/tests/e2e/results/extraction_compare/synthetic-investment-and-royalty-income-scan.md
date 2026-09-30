# synthetic-investment-and-royalty-income-scan.jpg


_Run: 2026-09-30 02:19 UTC_


## Durations

- bda: 21.58s extraction
- ocr-mapping: 1.906s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384
- us.amazon.nova-pro-v1:0: $0.01307680
- bda: $0.04000000
- **total: $0.05320064**

_By Extraction Method_
- shared (preclassification): $0.00933664
- ocr-mapping extraction: $0.00386400
- primary (bda): $0.04000000
- **total: $0.05320064**


## Accuracy

_By Extracted Data_
- BDA: 33% equivalent, 42% close, 58% misses
- OCR Mapping: 67% equivalent, 67% close, 33% misses

_By Geometry_
- BDA: 1/3 exact, 2 miss
- OCR Mapping: 3/3 exact, 0 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Geo | BDA Geometry | LLM Geometry |
|---|---|---|---|---|---|---|---|---|
| account_balance | $46,000.00 | ❌ - | ✅ 46000.00 | - | 1.0000 | - | - | 0.726,0.299,0.147,0.020 |
| account_holder_name | Alexis Morgan | ✅ Alexis Morgan | ✅ Alexis Morgan | 0.93 | 1.0000 | 0.053,0.145,0.101,0.011 | ✅ 0.053,0.145,0.101,0.011 | ✅ 0.053,0.145,0.101,0.011 |
| account_number | IRA-7821-****-5542 | ❌ - | ✅ IRA-7821-****-5542 | - | 0.9000 | 0.666,0.148,0.133,0.009 | ❌ - | ✅ 0.665,0.148,0.135,0.009 |
| account_type | Traditional IRA | ❌ - | ✅ Traditional IRA | - | 1.0000 | - | - | 0.665,0.165,0.101,0.009 |
| capital_gains_distributions_cumulative | - | - | - | 0.89 | - | - | - | - |
| contribution_dates | 2026-02-14, 2026-05-12 | ❌ - | ✅ 2026-02-14, 2026-05-12 | - | N/A | - | - | 0.059,0.590,0.074,0.009 |
| distribution_dates | 2026-07-20 | ❌ - | ✅ 2026-07-20 | - | 1.0000 | 0.059,0.630,0.074,0.008 | ❌ - | ✅ 0.059,0.629,0.075,0.009 |
| dividend_payments_cumulative | - | - | - | 0.90 | - | - | - | - |
| document_type | Brokerage Statement | ❌ IRA ACCOUNT STATEMENT | ❌ - | 0.38 | - | - | 0.750,0.050,0.212,0.010 | - |
| financial_institution | Harbor Brokerage Services, Inc. | 🟡 Harbor Brokerage Services | ✅ Harbor Brokerage Services, Inc. | 0.65 | 1.0000 | - | 0.135,0.044,0.345,0.020 | 0.666,0.182,0.121,0.011 |
| interest_credits_cumulative | - | - | - | 0.90 | - | - | - | - |
| statement_period_end | 2026-08-31 | ✅ 2026-08-31 | ❌ - | 0.83 | - | - | 0.793,0.131,0.113,0.011 | - |
| statement_period_start | 2026-01-01 | ✅ 2026-01-01 | ❌ - | 0.87 | - | - | 0.665,0.131,0.111,0.011 | - |
| tax_year | 2026 | ❌ - | ✅ 2026 | - | 1.0000 | - | - | 0.743,0.114,0.033,0.009 |
| total_value | 46000.00 | ✅ 46000 | ❌ - | 0.93 | - | - | 0.726,0.299,0.147,0.020 | - |
