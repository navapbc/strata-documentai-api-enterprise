# synthetic-investment-and-royalty-income-render-spanish.png


_Run: 2026-09-28 18:38 UTC_


## Durations

- bda: 22.74s extraction
- llm: 2.191s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384 (1956 in / 27 out)
- us.amazon.nova-pro-v1:0: $0.01291520 (14212 in / 483 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05303904**

_By Extraction Method_
- shared (preclassification): $0.00930144
- llm extraction: $0.00373760
- primary (bda): $0.04000000
- **total: $0.05303904**


## Accuracy
- BDA: 33% exact, 42% loose, 58% misses
- LLM: 58% exact, 58% loose, 42% misses


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_balance | $51,000.00 | ❌ - | ✅ $51,000.00 | - | 1.0000 | - | 0.857,0.423,0.082,0.011 | ❌ |
| account_holder_name | María Elena Vásquez | ✅ María Elena Vásquez | ✅ María Elena Vásquez | 0.79 | 0.9400 | 0.057,0.205,0.167,0.012 | 0.057,0.205,0.167,0.012 | ✅ |
| account_number | ***-***-6721 | ❌ - | ✅ ***-***-6721 | - | 0.7600 | - | 0.710,0.191,0.084,0.009 | ❌ |
| account_type | IRA Tradicional | ❌ - | ✅ IRA Tradicional | - | 1.0000 | - | 0.724,0.027,0.178,0.013 | ❌ |
| capital_gains_distributions_cumulative | - | - | - | 0.78 | - | - | - |  |
| contribution_dates | 03/10/2025, 06/15/2025 | ❌ - | ✅ 03/10/2025, 06/15/2025 | - | N/A | - | 0.057,0.562,0.072,0.008 | ❌ |
| distribution_dates | 11/20/2025 | ❌ - | ✅ 11/20/2025 | - | 1.0000 | - | 0.058,0.600,0.071,0.008 | ❌ |
| dividend_payments_cumulative | - | - | - | 0.92 | - | - | - |  |
| document_type | Brokerage Statement | ✅ Brokerage Statement | ❌ - | 0.75 | - | 0.097,0.088,0.070,0.010 | - | ❌ |
| financial_institution | Harbor Brokerage Services, LLC | ❌ Harbor Brokerage Services | ❌ Harbor Custody Trust Company | 0.57 | 1.0000 | 0.112,0.028,0.315,0.016 | 0.710,0.226,0.224,0.011 | ❌ |
| interest_credits_cumulative | - | - | - | 0.91 | - | - | - |  |
| statement_period_end | 2025-12-31 | ✅ 2025-12-31 | ❌ - | 0.86 | - | 0.865,0.079,0.088,0.009 | - | ❌ |
| statement_period_start | 2025-01-01 | ✅ 2025-01-01 | ❌ - | 0.80 | - | 0.754,0.079,0.088,0.009 | - | ❌ |
| tax_year | 2025 | ❌ - | ✅ 2025 | - | N/A | - | - |  |
| total_value | 51000.00 | 🟡 51000 | ❌ - | 0.91 | - | 0.856,0.423,0.083,0.011 | - | ❌ |
