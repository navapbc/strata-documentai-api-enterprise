# synthetic-assets-trust-funds-investment-accounts-render.pdf


_Run: 2026-09-28 18:33 UTC_


## Durations

- bda: 20.16s extraction
- llm: 2.615s extraction


## Cost

_By Service_
- us.amazon.nova-pro-v1:0: $0.01274800 (13651 in / 571 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05274800**

_By Extraction Method_
- shared (preclassification): $0.00880160
- llm extraction: $0.00394640
- primary (bda): $0.04000000
- **total: $0.05274800**


## Accuracy
- BDA: 50% exact, 70% loose, 30% misses
- LLM: 90% exact, 90% loose, 10% misses


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_balance | 100000.00 | 🟡 100000 | ✅ 100000.00 | 0.91 | 1.0000 | 0.788,0.552,0.090,0.012 | 0.788,0.552,0.090,0.012 | ✅ |
| account_number | XX-XX-3456 | ✅ XX-XX-3456 | ❌ Acct #: XX-XX-3456 | 0.88 | 1.0000 | 0.755,0.292,0.090,0.010 | 0.702,0.292,0.144,0.010 | ❌ |
| asset_types | Equity Securities, Fixed Income Securities, Real Estate Holdings, Cash and Cash Equivalents | ❌ - | ✅ Equity Securities, Fixed Income Securities, Real Estate Holdings, Cash and Cash Equivalents | - | N/A | - | 0.110,0.726,0.198,0.013 | ❌ |
| beneficiary_name | Jordan A. Rivera | ❌ Rivera Family Revocable Trust | ✅ Jordan A. Rivera | 0.08 | 0.9900 | 0.257,0.266,0.217,0.013 | 0.702,0.266,0.118,0.010 | ❌ |
| distributions_during_period | 2000.00 | 🟡 2000 | ✅ 2000.00 | 0.93 | 1.0000 | 0.807,0.500,0.070,0.012 | 0.807,0.500,0.070,0.012 | ✅ |
| statement_period_end | 2026-06-30 | ✅ 2026-06-30 | ✅ 2026-06-30 | 0.87 | 1.0000 | 0.833,0.167,0.079,0.010 | 0.834,0.167,0.078,0.010 | 🟡 |
| statement_period_start | 2026-01-01 | ✅ 2026-01-01 | ✅ 2026-01-01 | 0.86 | 1.0000 | 0.734,0.167,0.076,0.010 | 0.734,0.167,0.077,0.010 | 🟡 |
| trust_name | Rivera Family Revocable Trust | ❌ Jordan A. Rivera | ✅ Rivera Family Revocable Trust | 0.25 | 1.0000 | 0.702,0.266,0.118,0.010 | 0.257,0.266,0.217,0.013 | ❌ |
| trust_type | Revocable Trust | ✅ Revocable Trust | ✅ Revocable Trust | 0.92 | 1.0000 | 0.257,0.292,0.116,0.010 | 0.359,0.266,0.115,0.010 | ❌ |
| trustee_name | Cedar Grove Trust Company | ✅ Cedar Grove Trust Company | ✅ Cedar Grove Trust Company | 0.91 | 1.0000 | 0.233,0.126,0.055,0.013 | 0.093,0.125,0.303,0.017 | ❌ |
