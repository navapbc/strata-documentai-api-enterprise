# synthetic-investment-and-royalty-income-render-spanish.png


_Last run: 2026-10-28 20:03 UTC_


## Durations

- bda: 28.16s extraction
- ocr-mapping: 2.84s extraction


## Cost

_By Service_

- us.amazon.nova-lite-v1:0: $0.00012384
- us.amazon.nova-pro-v1:0: $0.01307120
- bda: $0.04000000
- analyze_document_layout: $0.00400000
- **total: $0.05719504**

_By Extraction Method_

- shared (preclassification): $0.00932384
- ocr-mapping extraction: $0.00787120
- primary (bda): $0.04000000
- **total: $0.05719504**


## Accuracy

_By Extracted Data_

- BDA: 7/12 (58%) equivalent match, 8/12 (67%) close, 4 misses
- OCR Mapping: 7/12 (58%) equivalent match, 7/12 (58%) close, 5 misses

_By Bounding Box_

- BDA: 3/6 exact, 3 miss
- OCR Mapping: 2/6 exact, 4 miss


## Field Comparison
| Field | Expected | BDA Value | OCR / LLM Value | BDA Conf | OCR / LLM Conf | Expected Bounding Box | BDA Bounding Box | OCR / LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| account_balance | $51,000.00 | ✅ $51,000.00 | ✅ 51000.00 | 0.68 | 1.0000 | 0.856,0.423,0.082,0.010 | ✅ 0.856,0.423,0.083,0.011 | ✅ 0.857,0.423,0.082,0.011 |
| account_holder_name | María Elena Vásquez | ✅ María Elena Vásquez | ✅ María Elena Vásquez | 0.82 | 0.9400 | 0.057,0.205,0.167,0.012 | ✅ 0.057,0.205,0.167,0.012 | ✅ 0.057,0.205,0.167,0.012 |
| account_number | ***-***-6721 | ✅ ***-***-6721 | ✅ ***-***-6721 | 0.71 | 0.7600 | 0.711,0.208,0.163,0.008 | ❌ 0.710,0.191,0.085,0.009 | ❌ 0.710,0.191,0.084,0.009 |
| account_type | IRA Tradicional | ✅ IRA Tradicional | ✅ IRA Tradicional | 0.91 | 1.0000 | 0.711,0.174,0.105,0.008 | ✅ 0.711,0.174,0.106,0.008 | ❌ 0.724,0.027,0.178,0.013 |
| capital_gains_distributions_cumulative | - | - | - | - | - | - | - | - |
| contribution_dates | 2025-03-10, 2025-06-15 | ✅ 2025-03-10, 2025-06-15 | ✅ 2025-03-10, 2025-06-15 | 0.72 | N/A | - | 0.057,0.544,0.072,0.008 | 0.057,0.562,0.072,0.008 |
| distribution_dates | 2025-11-20 | ✅ 2025-11-20 | ✅ 2025-11-20 | 0.81 | 1.0000 | - | 0.058,0.600,0.071,0.008 | 0.058,0.600,0.071,0.008 |
| dividend_payments_cumulative | - | - | - | - | - | - | - | - |
| document_type | Brokerage Statement | ❌ - | ❌ - | - | - | - | - | - |
| financial_institution | Harbor Brokerage Services, LLC | 🟡 Harbor Brokerage Services | ❌ Harbor Custody Trust Company | 0.24 | 1.0000 | 0.046,0.088,0.221,0.010 | ❌ 0.112,0.028,0.315,0.016 | ❌ 0.710,0.226,0.224,0.011 |
| interest_credits_cumulative | - | - | - | - | - | - | - | - |
| statement_period_end | 2025-12-31 | ❌ - | ❌ - | - | - | - | - | - |
| statement_period_start | 2025-01-01 | ❌ - | ❌ - | - | - | - | - | - |
| tax_year | 2025 | ✅ 2025 | ✅ 2025 | 0.21 | N/A | - | 0.165,0.342,0.080,0.009 | - |
| total_value | 51000.00 | ❌ - | ❌ - | - | - | 0.856,0.423,0.082,0.010 | ❌ - | ❌ - |
