# synthetic-investment-and-royalty-income-render.pdf


_Run: 2026-09-29 00:56 UTC_


## Durations

- bda: 41.06s extraction
- llm: 1.877s extraction


## Cost

_By Service_
- us.amazon.nova-pro-v1:0: $0.01225920 (13172 in / 538 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05225920**

_By Extraction Method_
- shared (preclassification): $0.00877600
- llm extraction: $0.00348320
- primary (bda): $0.04000000
- **total: $0.05225920**


## Accuracy
- BDA: 33% equivalent, 33% close, 67% misses
- LLM: 100% equivalent, 100% close, 0% misses


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_balance | $49,000.00 | ❌ - | ✅ 49000.00 | - | 1.0000 | - | 0.130,0.684,0.267,0.014 | ❌ |
| account_holder_name | Jordan Rivera | ✅ Jordan Rivera | ✅ Jordan Rivera | 0.91 | N/A | 0.117,0.254,0.112,0.012 | 0.116,0.228,0.135,0.012 | ❌ |
| account_number | xxxx-xxxx-1392 | ❌ - | ✅ xxxx-xxxx-1392 | - | 0.9100 | - | 0.526,0.259,0.271,0.011 | ❌ |
| account_type | Traditional IRA | ❌ - | ✅ Traditional IRA | - | 1.0000 | - | 0.525,0.229,0.265,0.011 | ❌ |
| capital_gains_distributions_cumulative | - | - | - | 0.91 | - | - | - |  |
| contribution_dates | - | - | ❌ 2025-01-01, 2025-12-31 | - | 1.0000 | - | 0.525,0.290,0.260,0.011 | ❌ |
| distribution_dates | - | - | ❌ 2025-01-01, 2025-12-31 | - | 1.0000 | - | 0.525,0.290,0.260,0.011 | ❌ |
| dividend_payments_cumulative | - | - | - | 0.92 | - | - | - |  |
| document_type | - | - | - | 0.06 | - | - | - |  |
| financial_institution | Seaport Financial Group | ✅ Seaport Financial Group | ✅ Seaport Financial Group | 0.88 | 0.9800 | 0.224,0.054,0.191,0.054 | 0.114,0.166,0.173,0.013 | ❌ |
| interest_credits_cumulative | - | - | - | 0.91 | - | - | - |  |
| statement_period_end | - | ❌ 2025-12-31 | - | 0.84 | - | 0.781,0.309,0.087,0.014 | - | ❌ |
| statement_period_start | - | ❌ 2025-01-01 | - | 0.81 | - | 0.679,0.308,0.098,0.014 | - | ❌ |
| tax_year | 2025 | ❌ - | ✅ 2025 | - | 1.0000 | - | 0.525,0.290,0.260,0.011 | ❌ |
| total_value | - | ❌ 49000 | - | 0.93 | - | 0.778,0.683,0.088,0.014 | - | ❌ |
