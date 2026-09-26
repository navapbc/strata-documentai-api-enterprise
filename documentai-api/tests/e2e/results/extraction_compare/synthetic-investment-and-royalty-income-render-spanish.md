_Run: 2026-09-26 22:38 UTC_


## synthetic-investment-and-royalty-income-render-spanish.png

**Durations**

- bda: 22.28s extraction
- llm: 2.061s extraction

**Cost**

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384 (1956 in / 27 out)
- us.amazon.nova-pro-v1:0: $0.01311360 (14212 in / 545 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05323744**

_By Extraction Method_
- shared (preclassification): $0.00927904
- llm extraction: $0.00395840
- primary (bda): $0.04000000
- **total: $0.05323744**

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_balance | - | - | $51,000.00 | - | 1.0000 | - | 0.056,0.423,0.192,0.009 | ❌ |
| account_holder_name | - | María Elena Vásquez | María Elena Vásquez | 0.79 | N/A | 0.057,0.205,0.167,0.012 | 0.056,0.178,0.157,0.009 | ❌ |
| account_number | - | - | ***-***-6721 | - | 0.9900 | - | 0.487,0.191,0.082,0.009 | ❌ |
| account_type | - | - | IRA Tradicional | - | 1.0000 | - | 0.562,0.027,0.340,0.013 | ❌ |
| capital_gains_distributions_cumulative | - | - | - | 0.78 | - | - | - |  |
| contribution_dates | - | - | 03/10/2025, 06/15/2025 | - | N/A | - | 0.057,0.544,0.072,0.008 | ❌ |
| distribution_dates | - | - | 11/20/2025 | - | 1.0000 | - | 0.058,0.600,0.071,0.008 | ❌ |
| dividend_payments_cumulative | - | - | - | 0.92 | - | - | - |  |
| document_type | - | Brokerage Statement | - | 0.75 | - | 0.097,0.088,0.070,0.010 | - | ❌ |
| financial_institution | - | Harbor Brokerage Services | Harbor Brokerage Services, LLC | 0.57 | 1.0000 | 0.112,0.028,0.315,0.016 | 0.045,0.088,0.222,0.010 | ❌ |
| interest_credits_cumulative | - | - | - | 0.91 | - | - | - |  |
| statement_period_end | - | 2025-12-31 | - | 0.86 | - | 0.865,0.079,0.088,0.009 | - | ❌ |
| statement_period_start | - | 2025-01-01 | - | 0.80 | - | 0.754,0.079,0.088,0.009 | - | ❌ |
| tax_year | - | - | 2025 | - | 0.9800 | - | 0.474,0.080,0.150,0.008 | ❌ |
| total_value | - | 51000 | - | 0.91 | - | 0.856,0.423,0.083,0.011 | - | ❌ |
