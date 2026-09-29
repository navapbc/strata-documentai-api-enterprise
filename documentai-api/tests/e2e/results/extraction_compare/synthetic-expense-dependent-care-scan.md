# synthetic-expense-dependent-care-scan.png


_Run: 2026-09-29 16:06 UTC_


## Durations

- bda: 27.98s extraction
- llm: 2.333s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384 (1956 in / 27 out)
- us.amazon.nova-pro-v1:0: $0.01374080 (14884 in / 573 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05386464**

_By Extraction Method_
- shared (preclassification): $0.00927264
- llm extraction: $0.00459200
- primary (bda): $0.04000000
- **total: $0.05386464**


## Accuracy
- BDA: 82% equivalent, 82% close, 18% misses
- LLM: 82% equivalent, 82% close, 18% misses


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| amount_paid | 650.00 | ✅ 650 | ✅ 650.00 | 0.80 | 0.9900 | 0.860,0.658,0.061,0.011 | 0.861,0.718,0.072,0.011 | ❌ |
| balance_due | 650.00 | ✅ 650 | ✅ 650.00 | 0.94 | 1.0000 | 0.868,0.743,0.065,0.012 | 0.860,0.658,0.061,0.011 | ❌ |
| dependent_names | Elliot James Morgan | ❌ - | ✅ Elliot James Morgan | - | 1.0000 | - | 0.065,0.342,0.154,0.012 | ❌ |
| document_type | Dependent Care Expense Statement | ✅ DEPENDENT CARE EXPENSE STATEMENT | ❌ expense statement | 0.88 | 1.0000 | 0.655,0.046,0.261,0.035 | 0.655,0.068,0.261,0.014 | ❌ |
| payment_amount | 325.00 | ✅ 325 | ✅ 325.00 | 0.78 | 1.0000 | 0.722,0.466,0.061,0.011 | 0.723,0.466,0.061,0.011 | 🟡 |
| payment_frequency | Weekly | ❌ - | ❌ biweekly | 0.80 | 0.9900 | - | 0.248,0.376,0.045,0.012 | ❌ |
| provider_address | 321 Whispering Pines Drive Holly Springs, NC 27540 | ✅ 321 Whispering Pines Drive Holly Springs, NC 27540 | ✅ 321 Whispering Pines Drive, Holly Springs, NC 27540 | 0.91 | N/A | 0.219,0.071,0.207,0.029 | 0.219,0.071,0.207,0.012 | ❌ |
| provider_name | Pine Ridge Family Learning Center | ✅ Pine Ridge Family Learning Center | ✅ Pine Ridge Family Learning Center | 0.93 | 1.0000 | 0.219,0.049,0.336,0.015 | 0.219,0.049,0.337,0.015 | 🟡 |
| service_end_date | 2026-08-30 | ✅ 2026-08-30 | ✅ 2026-08-30 | 0.77 | 0.9100 | 0.859,0.123,0.083,0.009 | 0.859,0.123,0.083,0.009 | ✅ |
| service_start_date | 2026-08-03 | ✅ 2026-08-03 | ✅ 2026-08-03 | 0.79 | 0.9100 | 0.758,0.123,0.091,0.010 | 0.607,0.123,0.334,0.010 | ❌ |
| statement_date | 2026-09-02 | ✅ 2026-09-02 | ✅ 2026-09-02 | 0.84 | 1.0000 | 0.758,0.103,0.083,0.009 | 0.757,0.103,0.083,0.009 | 🟡 |
