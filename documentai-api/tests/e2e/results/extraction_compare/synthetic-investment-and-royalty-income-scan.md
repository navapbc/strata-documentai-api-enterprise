# synthetic-investment-and-royalty-income-scan.jpg


_Run: 2026-10-01 02:38 UTC_


## Durations

- bda: 22.27s extraction
- ocr-mapping: 1.404s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384
- us.amazon.nova-pro-v1:0: $0.01303520
- bda: $0.04000000
- **total: $0.05315904**

_By Extraction Method_
- shared (preclassification): $0.00928224
- ocr-mapping extraction: $0.00387680
- primary (bda): $0.04000000
- **total: $0.05315904**


## Accuracy

_By Extracted Data_
- BDA: 4/12 (33%) equivalent match, 5/12 (42%) close, 7 misses
- OCR Mapping: 8/12 (67%) equivalent match, 8/12 (67%) close, 4 misses

_By Bounding Box_
- BDA: 1/5 exact, 4 miss
- OCR Mapping: 3/5 exact, 2 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Bounding Box | BDA Bounding Box | LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| account_balance | $46,000.00 | ❌ - | ✅ 46000.00 | - | 1.0000 | - | - | 0.726,0.299,0.147,0.020 |
| account_holder_name | Alexis Morgan | ✅ Alexis Morgan | ✅ Alexis Morgan | 0.93 | 1.0000 | 0.053,0.145,0.101,0.011 | ✅ 0.053,0.145,0.101,0.011 | ✅ 0.053,0.145,0.101,0.011 |
| account_number | IRA-7821-****-5542 | ❌ - | ✅ IRA-7821-****-5542 | - | 0.9000 | 0.666,0.148,0.133,0.009 | ❌ - | ✅ 0.665,0.148,0.135,0.009 |
| account_type | Traditional IRA | ❌ - | ✅ Traditional IRA | - | 1.0000 | 0.508,0.165,0.258,0.010 | ❌ - | ❌ 0.665,0.165,0.101,0.009 |
| capital_gains_distributions_cumulative | - | - | - | 0.89 | - | - | - | - |
| contribution_dates | 2026-02-14, 2026-05-12 | ❌ - | ✅ 2026-02-14, 2026-05-12 | - | N/A | - | - | 0.059,0.590,0.074,0.009 |
| distribution_dates | 2026-07-20 | ❌ - | ✅ 2026-07-20 | - | 1.0000 | 0.059,0.630,0.074,0.008 | ❌ - | ✅ 0.059,0.629,0.075,0.009 |
| dividend_payments_cumulative | - | - | - | 0.90 | - | - | - | - |
| document_type | Brokerage Statement | ❌ IRA ACCOUNT STATEMENT | ❌ - | 0.38 | - | - | 0.750,0.050,0.212,0.010 | - |
| financial_institution | Harbor Brokerage Services, Inc. | 🟡 Harbor Brokerage Services | ✅ Harbor Brokerage Services, Inc. | 0.65 | 1.0000 | 0.054,0.174,0.826,0.019 | ❌ 0.135,0.044,0.345,0.020 | ❌ 0.666,0.182,0.121,0.011 |
| interest_credits_cumulative | - | - | - | 0.90 | - | - | - | - |
| statement_period_end | 2026-08-31 | ✅ 2026-08-31 | ❌ - | 0.83 | - | - | 0.793,0.131,0.113,0.011 | - |
| statement_period_start | 2026-01-01 | ✅ 2026-01-01 | ❌ - | 0.87 | - | - | 0.665,0.131,0.111,0.011 | - |
| tax_year | 2026 | ❌ - | ✅ 2026 | - | 1.0000 | - | - | 0.743,0.114,0.033,0.009 |
| total_value | 46000.00 | ✅ 46000 | ❌ - | 0.93 | - | - | 0.726,0.299,0.147,0.020 | - |
