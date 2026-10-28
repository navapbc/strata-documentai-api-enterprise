# synthetic-investment-and-royalty-income-scan.jpg


_Run: 2026-10-28 18:36 UTC_


## Durations

- bda: 25.93s extraction
- ocr-mapping: 3.094s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384 (1956 in / 27 out)
- us.amazon.nova-pro-v1:0: $0.01306080 (14374 in / 488 out)
- bda: $0.04000000 (1 page(s))
- analyze_document_layout: $0.00400000 (1 page(s))
- **total: $0.05718464**

_By Extraction Method_
- shared (preclassification): $0.00930784
- ocr-mapping extraction: $0.00787680
- primary (bda): $0.04000000
- **total: $0.05718464**


## Accuracy

_By Extracted Data_
- BDA: 8/12 (67%) equivalent match, 8/12 (67%) close, 4 misses
- OCR Mapping: 8/12 (67%) equivalent match, 8/12 (67%) close, 4 misses

_By Bounding Box_
- BDA: 3/5 exact, 2 miss
- OCR Mapping: 3/5 exact, 2 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Bounding Box | BDA Bounding Box | LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| account_balance | $46,000.00 | ✅ $46,000.00 | ✅ 46000.00 | 0.43 | 1.0000 | - | 0.527,0.349,0.077,0.011 | 0.726,0.299,0.147,0.020 |
| account_holder_name | Alexis Morgan | ✅ Alexis Morgan | ✅ Alexis Morgan | 0.92 | 1.0000 | 0.053,0.145,0.101,0.011 | ✅ 0.053,0.145,0.101,0.011 | ✅ 0.053,0.145,0.101,0.011 |
| account_number | IRA-7821-****-5542 | ✅ IRA-7821-****-5542 | ✅ IRA-7821-****-5542 | 0.74 | 0.9000 | 0.666,0.148,0.133,0.009 | ✅ 0.665,0.148,0.135,0.009 | ✅ 0.665,0.148,0.135,0.009 |
| account_type | Traditional IRA | ✅ Traditional IRA | ✅ Traditional IRA | 0.86 | 1.0000 | 0.508,0.165,0.258,0.010 | ❌ 0.665,0.165,0.101,0.009 | ❌ 0.665,0.165,0.101,0.009 |
| capital_gains_distributions_cumulative | - | - | - | - | - | - | - | - |
| contribution_dates | 2026-02-14, 2026-05-12 | ✅ 2026-02-14, 2026-05-12 | ✅ 2026-02-14, 2026-05-12 | 0.78 | N/A | - | 0.059,0.570,0.074,0.009 | 0.059,0.590,0.074,0.009 |
| distribution_dates | 2026-07-20 | ✅ 2026-07-20 | ✅ 2026-07-20 | 0.93 | 1.0000 | 0.059,0.630,0.074,0.008 | ✅ 0.059,0.629,0.075,0.009 | ✅ 0.059,0.629,0.075,0.009 |
| dividend_payments_cumulative | - | - | - | - | - | - | - | - |
| document_type | Brokerage Statement | ❌ - | ❌ - | - | - | - | - | - |
| financial_institution | Harbor Brokerage Services, Inc. | ✅ Harbor Brokerage Services, Inc. | ✅ Harbor Brokerage Services, Inc. | 0.75 | 1.0000 | 0.054,0.174,0.826,0.019 | ❌ 0.135,0.044,0.345,0.020 | ❌ 0.666,0.182,0.121,0.011 |
| interest_credits_cumulative | - | - | - | - | - | - | - | - |
| statement_period_end | 2026-08-31 | ❌ - | ❌ - | - | - | - | - | - |
| statement_period_start | 2026-01-01 | ❌ - | ❌ - | - | - | - | - | - |
| tax_year | 2026 | ✅ 2026 | ✅ 2026 | 0.73 | 1.0000 | - | 0.665,0.199,0.034,0.009 | 0.743,0.114,0.033,0.009 |
| total_value | 46000.00 | ❌ - | ❌ - | - | - | - | - | - |
