# synthetic-expense-burial-scan-corner-torn.jpg


_Run: 2026-09-28 18:34 UTC_


## Durations

- bda: 20.05s extraction
- llm: 2.168s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384 (1956 in / 27 out)
- us.amazon.nova-pro-v1:0: $0.01348640 (14402 in / 614 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05361024**

_By Extraction Method_
- shared (preclassification): $0.00929184
- llm extraction: $0.00431840
- primary (bda): $0.04000000
- **total: $0.05361024**


## Accuracy
- BDA: 44% exact, 67% loose, 33% misses
- LLM: 78% exact, 78% loose, 22% misses


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_balance | 2750.00 | 🟡 2750 | ✅ 2750.00 | 0.93 | 1.0000 | 0.837,0.623,0.072,0.012 | 0.092,0.461,0.305,0.014 | ❌ |
| account_number | ***-***-7429 | ❌ ***_***-7429 | ❌ ***_***-7429 | 0.27 | 0.9700 | 0.696,0.261,0.085,0.010 | 0.538,0.260,0.242,0.010 | ❌ |
| asset_types | Cash | ❌ - | ✅ Cash | - | 1.0000 | - | 0.701,0.389,0.203,0.011 | ❌ |
| beneficiary_name | Payable to Estate | ✅ Payable to Estate | ✅ Payable to Estate | 0.80 | 1.0000 | 0.559,0.754,0.128,0.012 | 0.559,0.754,0.128,0.012 | ✅ |
| distributions_during_period | 0.00 | ❌ - | ✅ 0.00 | 0.93 | N/A | 0.579,0.412,0.041,0.011 | 0.743,0.404,0.120,0.010 | ❌ |
| statement_period_end | 2026-08-31 | ✅ 2026-08-31 | ✅ 2026-08-31 | 0.85 | 0.9600 | 0.775,0.202,0.127,0.012 | 0.538,0.302,0.398,0.013 | ❌ |
| statement_period_start | 2026-01-01 | ✅ 2026-01-01 | ✅ 2026-01-01 | 0.86 | 0.9600 | 0.696,0.302,0.110,0.011 | 0.538,0.302,0.398,0.013 | ❌ |
| trust_name | - | - | ❌ Irrevocable Burial Trust Account | 0.24 | 1.0000 | - | 0.697,0.240,0.222,0.010 | ❌ |
| trust_type | Irrevocable Burial Trust Account | ✅ Irrevocable Burial Trust Account | ❌ Irrevocable | 0.88 | 1.0000 | 0.697,0.240,0.222,0.010 | 0.697,0.240,0.222,0.010 | ✅ |
| trustee_name | Cedar Grove Burial Trust Company | 🟡 CEDAR GROVE BURIAL TRUST COMPANY | ✅ Cedar Grove Burial Trust Company | 0.79 | 1.0000 | 0.209,0.073,0.348,0.039 | 0.209,0.097,0.348,0.016 | ❌ |
