# synthetic-insurance-health-insurance-premium-render-spanish.png


_Run: 2026-09-29 00:55 UTC_


## Durations

- bda: 29.1s extraction
- llm: 2.249s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384 (1956 in / 27 out)
- us.amazon.nova-pro-v1:0: $0.01421120 (15260 in / 626 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05433504**

_By Extraction Method_
- shared (preclassification): $0.00929504
- llm extraction: $0.00504000
- primary (bda): $0.04000000
- **total: $0.05433504**


## Accuracy
- BDA: 91% equivalent, 100% close, 0% misses
- LLM: 73% equivalent, 73% close, 27% misses


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| coverage_end_date | 2026-08-31 | ✅ 2026-08-31 | ✅ 2026-08-31 | 0.69 | 0.9900 | 0.436,0.278,0.035,0.010 | 0.350,0.242,0.195,0.010 | ❌ |
| coverage_start_date | 2026-08-01 | ✅ 2026-08-01 | ✅ 2026-08-01 | 0.75 | 0.9900 | 0.487,0.265,0.050,0.009 | 0.337,0.242,0.209,0.010 | ❌ |
| employer_name | - | - | - | 0.91 | N/A | - | - |  |
| insurer_or_marketplace_name | Harbor Health Plan, Inc. | 🟡 Harbor Health Plan | ✅ Harbor Health Plan, Inc. | 0.26 | 1.0000 | 0.127,0.036,0.201,0.044 | 0.433,0.035,0.107,0.010 | ❌ |
| payment_due_date | 2026-08-25 | ✅ 2026-08-25 | ✅ 2026-08-25 | 0.10 | 1.0000 | 0.387,0.327,0.126,0.012 | 0.336,0.327,0.176,0.012 | ❌ |
| payment_frequency | Mensual | ✅ mensual | ❌ monthly | 0.62 | 0.9900 | 0.709,0.251,0.055,0.008 | 0.631,0.251,0.133,0.008 | ❌ |
| payment_status | Paid | ✅ Paid | ✅ Paid | 0.72 | 1.0000 | - | 0.630,0.390,0.095,0.010 | ❌ |
| policy_or_member_id | MEM-87X4-3K2L | ✅ MEM-87X4-3K2L | ✅ MEM-87X4-3K2L | 0.89 | 0.9900 | 0.731,0.127,0.133,0.009 | 0.731,0.127,0.132,0.009 | 🟡 |
| policyholder_name | María Elena Salazar | ✅ María Elena Salazar | ✅ María Elena Salazar | 0.77 | 0.9900 | 0.049,0.242,0.165,0.011 | 0.049,0.242,0.165,0.010 | 🟡 |
| premium_amount | 260.00 | ✅ 260 | ❌ 450.00 | 0.89 | 1.0000 | 0.866,0.334,0.065,0.011 | 0.877,0.251,0.055,0.010 | ❌ |
| statement_date | 2026-09-02 | ✅ 2026-09-02 | ✅ 2026-09-02 | 0.77 | 0.9900 | 0.731,0.050,0.186,0.011 | 0.731,0.050,0.186,0.011 | ✅ |
| subsidy_or_tax_credit_amount | 225.00 | ✅ 225 | ❌ -225.00 | 0.81 | 1.0000 | 0.873,0.278,0.059,0.010 | 0.873,0.278,0.059,0.010 | ✅ |
