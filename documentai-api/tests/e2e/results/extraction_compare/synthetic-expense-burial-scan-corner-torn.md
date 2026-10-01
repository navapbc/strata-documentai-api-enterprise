# synthetic-expense-burial-scan-corner-torn.jpg


_Run: 2026-10-01 01:41 UTC_


## Durations

- bda: 26.36s extraction
- ocr-mapping: 1.964s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384
- us.amazon.nova-pro-v1:0: $0.01361360
- bda: $0.04000000
- **total: $0.05373744**

_By Extraction Method_
- shared (preclassification): $0.00931104
- ocr-mapping extraction: $0.00442640
- primary (bda): $0.04000000
- **total: $0.05373744**


## Accuracy

_By Extracted Data_
- BDA: 67% equivalent, 67% close, 33% misses
- OCR Mapping: 67% equivalent, 67% close, 33% misses

_By Bounding Box_
- BDA: 1/3 exact, 2 miss
- OCR Mapping: 0/2 exact, 2 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Bounding Box | BDA Bounding Box | LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| account_balance | 2750.00 | ✅ 2750 | ✅ 2750.00 | 0.93 | 1.0000 | 0.731,0.445,0.140,0.021 | ❌ 0.837,0.623,0.072,0.012 | ❌ 0.092,0.461,0.305,0.014 |
| account_number | ***-***-7429 | ❌ ***_***-7429 | ❌ ***_***-7429 | 0.27 | 0.9700 | - | 0.696,0.261,0.085,0.010 | 0.538,0.260,0.242,0.010 |
| asset_types | Cash | ❌ - | ✅ Cash | - | 1.0000 | - | - | 0.701,0.389,0.203,0.011 |
| beneficiary_name | Payable to Estate | ✅ Payable to Estate | ❌ - | 0.80 | N/A | 0.559,0.754,0.127,0.011 | ✅ 0.559,0.754,0.128,0.012 | ❌ - |
| distributions_during_period | 0.00 | ❌ - | ✅ 0.00 | 0.93 | N/A | - | 0.579,0.412,0.041,0.011 | 0.743,0.404,0.120,0.010 |
| statement_period_end | 2026-08-31 | ✅ 2026-08-31 | ✅ 2026-08-31 | 0.85 | 0.9600 | - | 0.775,0.202,0.127,0.012 | 0.538,0.302,0.398,0.013 |
| statement_period_start | 2026-01-01 | ✅ 2026-01-01 | ✅ 2026-01-01 | 0.86 | 0.9600 | 0.082,0.574,0.078,0.009 | ❌ 0.696,0.302,0.110,0.011 | ❌ 0.538,0.302,0.398,0.013 |
| trust_name | - | - | ❌ Irrevocable Burial Trust Account | 0.24 | 1.0000 | - | - | 0.697,0.240,0.222,0.010 |
| trust_type | Irrevocable Burial Trust Account | ✅ Irrevocable Burial Trust Account | ❌ Irrevocable | 0.88 | 1.0000 | - | 0.697,0.240,0.222,0.010 | 0.697,0.240,0.222,0.010 |
| trustee_name | Cedar Grove Burial Trust Company | ✅ CEDAR GROVE BURIAL TRUST COMPANY | ✅ Cedar Grove Burial Trust Company | 0.79 | 1.0000 | - | 0.209,0.073,0.348,0.039 | 0.209,0.097,0.348,0.016 |
