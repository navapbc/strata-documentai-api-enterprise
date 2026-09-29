# synthetic-expense-burial-scan-corner-torn.jpg


_Run: 2026-09-29 16:06 UTC_


## Durations

- bda: 20.16s extraction
- llm: 2.191s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012360 (1956 in / 26 out)
- us.amazon.nova-pro-v1:0: $0.01330640 (14573 in / 515 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05343000**

_By Extraction Method_
- shared (preclassification): $0.00925960
- llm extraction: $0.00417040
- primary (bda): $0.04000000
- **total: $0.05343000**


## Accuracy
- BDA: 67% equivalent, 67% close, 33% misses
- LLM: 78% equivalent, 78% close, 22% misses


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_balance | 2750.00 | ✅ 2750 | ✅ 2750.00 | 0.93 | 1.0000 | 0.837,0.623,0.072,0.012 | 0.732,0.445,0.140,0.021 | ❌ |
| account_number | ***-***-7429 | ❌ ***_***-7429 | ❌ ***_***-7429 | 0.28 | 0.9700 | 0.696,0.261,0.084,0.010 | 0.696,0.261,0.084,0.010 | ✅ |
| asset_types | Cash | ❌ - | ✅ Cash | - | 1.0000 | - | 0.701,0.389,0.203,0.011 | ❌ |
| beneficiary_name | Payable to Estate | ✅ Payable to Estate | ✅ Payable to Estate | 0.80 | 1.0000 | 0.559,0.754,0.128,0.012 | 0.559,0.754,0.128,0.012 | ✅ |
| distributions_during_period | 0.00 | ❌ - | ✅ 0.00 | 0.93 | 1.0000 | 0.579,0.412,0.041,0.011 | 0.579,0.412,0.041,0.011 | ✅ |
| statement_period_end | 2026-08-31 | ✅ 2026-08-31 | ✅ 2026-08-31 | 0.85 | 1.0000 | 0.775,0.202,0.127,0.012 | 0.775,0.202,0.127,0.012 | ✅ |
| statement_period_start | 2026-01-01 | ✅ 2026-01-01 | ✅ 2026-01-01 | 0.86 | 0.9600 | 0.696,0.302,0.110,0.011 | 0.696,0.302,0.241,0.011 | ❌ |
| trust_name | - | - | ❌ Irrevocable Burial Trust Account | 0.26 | 1.0000 | - | 0.697,0.240,0.222,0.010 | ❌ |
| trust_type | Irrevocable Burial Trust Account | ✅ Irrevocable Burial Trust Account | ❌ Irrevocable | 0.88 | 1.0000 | 0.697,0.240,0.222,0.010 | 0.697,0.240,0.077,0.010 | ❌ |
| trustee_name | Cedar Grove Burial Trust Company | ✅ CEDAR GROVE BURIAL TRUST COMPANY | ✅ Cedar Grove Burial Trust Company | 0.82 | 1.0000 | 0.209,0.073,0.348,0.039 | 0.209,0.097,0.348,0.016 | ❌ |
