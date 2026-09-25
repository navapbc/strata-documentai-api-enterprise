_Run: 2026-09-25 16:55 UTC_


## synthetic-expense-burial-scan-corner-torn.jpg

**Durations**

- bda: 20.7s extraction
- llm: 2.166s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_balance | - | 2750 | 2750.00 | 0.93 | 1.0000 | 0.837,0.623,0.072,0.012 | 0.092,0.461,0.305,0.014 | ❌ |
| account_number | - | ***_***-7429 | ***_***-7429 | 0.28 | 0.9700 | 0.696,0.261,0.084,0.010 | 0.538,0.260,0.242,0.010 | ❌ |
| asset_types | - | - | Cash | - | 1.0000 | - | 0.092,0.461,0.208,0.011 | ❌ |
| beneficiary_name | - | Payable to Estate | Payable to Estate | 0.80 | N/A | 0.559,0.754,0.128,0.012 | 0.586,0.713,0.191,0.011 | ❌ |
| distributions_during_period | - | - | 0.00 | 0.93 | N/A | 0.579,0.412,0.041,0.011 | 0.743,0.404,0.120,0.010 | ❌ |
| statement_period_end | - | 2026-08-31 | 2026-08-31 | 0.85 | 0.9600 | 0.775,0.202,0.127,0.012 | 0.538,0.302,0.398,0.013 | ❌ |
| statement_period_start | - | 2026-01-01 | 2026-01-01 | 0.86 | 0.9600 | 0.696,0.302,0.110,0.011 | 0.538,0.302,0.398,0.013 | ❌ |
| trust_name | - | - | Irrevocable Burial Trust Account | 0.26 | 1.0000 | - | 0.697,0.240,0.222,0.010 | ❌ |
| trust_type | - | Irrevocable Burial Trust Account | Irrevocable | 0.88 | 1.0000 | 0.697,0.240,0.222,0.010 | 0.697,0.240,0.222,0.010 | ✅ |
| trustee_name | - | CEDAR GROVE BURIAL TRUST COMPANY | Cedar Grove Burial Trust Company | 0.82 | 1.0000 | 0.209,0.073,0.348,0.039 | 0.209,0.097,0.348,0.016 | ❌ |
