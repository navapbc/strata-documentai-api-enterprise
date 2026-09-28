# Extraction Compare Results

_Run: 2026-09-28 14:46 UTC_

## Avg Durations
- bda: 24.84s
- llm: 4.55s
- textract: 2.15s


## Total Cost by Model
- us.amazon.nova-lite-v1:0: $0.002914
- us.amazon.nova-pro-v1:0: $0.554532
- **total: $0.557446**


## Primary Extraction vs. LLM via Textract
| Primary Method | Shared (preclass) | Primary Total | LLM Total | LLM vs Primary | Median Primary Duration | Median LLM Duration | LLM vs Primary |
|---|---|---|---|---|---|---|---|
| bda | $0.317988 | $1.400000 | $0.224141 | 6.2x cheaper | 23.86s | 2.40s | 9.9x faster |
| textract | $0.008854 | $0.025000 | $0.006463 | 3.9x cheaper | 2.15s | 2.25s | 1.0x slower |


## Document Summary

| Document | Method | Total Cost | Primary Cost | LLM Cost | Cost Delta | Primary Duration | LLM Duration | Duration Delta |
|---|---|---|---|---|---|---|---|---|
| [synthetic-assets-bank-statement-render-spanish.png](synthetic-assets-bank-statement-render-spanish.md) | bda | $0.059328 | $0.049330 | $0.019328 | -0.030002 | 31.25s | 17.03s | -14.22s |
| [synthetic-assets-bank-statement-render.pdf](synthetic-assets-bank-statement-render.md) | bda | $0.054264 | $0.048760 | $0.014264 | -0.034496 | 22.80s | 3.42s | -19.39s |
| [synthetic-assets-bank-statement-scan.jpg](synthetic-assets-bank-statement-scan.md) | bda | $0.058475 | $0.049257 | $0.018475 | -0.030782 | 25.03s | 12.62s | -12.41s |
| [synthetic-assets-life-insurance-policy-render.pdf](synthetic-assets-life-insurance-policy-render.md) | bda | $0.052354 | $0.048805 | $0.012354 | -0.036451 | 22.91s | 1.53s | -21.38s |
| [synthetic-assets-life-insurance-policy-scan.jpg](synthetic-assets-life-insurance-policy-scan.md) | bda | $0.053170 | $0.049260 | $0.013170 | -0.036090 | 22.94s | 4.47s | -18.47s |
| [synthetic-assets-trust-funds-investment-accounts-render-spanish.png](synthetic-assets-trust-funds-investment-accounts-render-spanish.md) | bda | $0.053891 | $0.049295 | $0.013891 | -0.035404 | 23.44s | 1.77s | -21.67s |
| [synthetic-assets-trust-funds-investment-accounts-render.pdf](synthetic-assets-trust-funds-investment-accounts-render.md) | bda | $0.052735 | $0.048789 | $0.012735 | -0.036054 | 22.01s | 5.14s | -16.87s |
| [synthetic-assets-trust-funds-investment-accounts-scan.jpg](synthetic-assets-trust-funds-investment-accounts-scan.md) | bda | $0.053724 | $0.049279 | $0.013724 | -0.035554 | 23.14s | 2.14s | -21.00s |
| [synthetic-expense-burial-scan-corner-torn.jpg](synthetic-expense-burial-scan-corner-torn.md) | bda | $0.053559 | $0.049266 | $0.013559 | -0.035707 | 21.61s | 2.02s | -19.59s |
| [synthetic-expense-child-support-rendered.pdf](synthetic-expense-child-support-rendered.md) | bda | $0.053294 | $0.048770 | $0.013294 | -0.035475 | 25.94s | 1.20s | -24.75s |
| [synthetic-expense-child-support-scan.jpg](synthetic-expense-child-support-scan.md) | bda | $0.055496 | $0.049304 | $0.015496 | -0.033809 | 34.84s | 2.17s | -32.67s |
| [synthetic-expense-child-support-spanish-picture.png](synthetic-expense-child-support-spanish-picture.md) | bda | $0.055615 | $0.049308 | $0.015615 | -0.033693 | 27.56s | 2.03s | -25.53s |
| [synthetic-expense-dependent-care-render.pdf](synthetic-expense-dependent-care-render.md) | bda | $0.052843 | $0.048805 | $0.012843 | -0.035962 | 22.98s | 2.86s | -20.12s |
| [synthetic-expense-dependent-care-scan.png](synthetic-expense-dependent-care-scan.md) | bda | $0.053981 | $0.049266 | $0.013981 | -0.035286 | 26.02s | 2.72s | -23.30s |
| [synthetic-expense-utility-cable-bill-render-spanish.png](synthetic-expense-utility-cable-bill-render-spanish.md) | bda | $0.055802 | $0.049276 | $0.015802 | -0.033474 | 37.31s | 3.62s | -33.69s |
| [synthetic-expense-utility-cable-bill-render.pdf](synthetic-expense-utility-cable-bill-render.md) | bda | $0.053272 | $0.048776 | $0.013272 | -0.035504 | 25.90s | 1.95s | -23.95s |
| [synthetic-expense-utility-electric-bill-render-spanish.png](synthetic-expense-utility-electric-bill-render-spanish.md) | bda | $0.059339 | $0.049263 | $0.019339 | -0.029924 | 23.99s | 8.13s | -15.86s |
| [synthetic-expense-utility-electric-bill-render.pdf](synthetic-expense-utility-electric-bill-render.md) | bda | $0.059695 | $0.048802 | $0.019695 | -0.029106 | 24.27s | 16.94s | -7.33s |
| [synthetic-expense-utility-electric-bill-scan.jpg](synthetic-expense-utility-electric-bill-scan.md) | bda | $0.059051 | $0.049289 | $0.019051 | -0.030238 | 33.29s | 7.51s | -25.78s |
| [synthetic-expense-utility-water-sewer-bill-render-spanish.png](synthetic-expense-utility-water-sewer-bill-render-spanish.md) | bda | $0.057964 | $0.049273 | $0.017964 | -0.031310 | 28.78s | 3.81s | -24.98s |
| [synthetic-expense-utility-water-sewer-bill-render.pdf](synthetic-expense-utility-water-sewer-bill-render.md) | bda | $0.056446 | $0.048792 | $0.016446 | -0.032346 | 21.82s | 3.12s | -18.70s |
| [synthetic-expense-utility-water-sewer-bill-scan.jpg](synthetic-expense-utility-water-sewer-bill-scan.md) | bda | $0.057324 | $0.049334 | $0.017324 | -0.032010 | 24.66s | 3.70s | -20.96s |
| [synthetic-insurance-health-insurance-premium-render-spanish.png](synthetic-insurance-health-insurance-premium-render-spanish.md) | bda | $0.054256 | $0.049353 | $0.014256 | -0.035097 | 25.94s | 1.94s | -24.00s |
| [synthetic-insurance-health-insurance-premium-render.pdf](synthetic-insurance-health-insurance-premium-render.md) | bda | $0.053409 | $0.048802 | $0.013409 | -0.035393 | 27.83s | 2.03s | -25.80s |
| [synthetic-insurance-health-insurance-premium-scan.jpg](synthetic-insurance-health-insurance-premium-scan.md) | bda | $0.054143 | $0.049337 | $0.014143 | -0.035194 | 21.01s | 2.14s | -18.87s |
| [synthetic-investment-and-royalty-income-render-spanish.png](synthetic-investment-and-royalty-income-render-spanish.md) | bda | $0.053237 | $0.049279 | $0.013237 | -0.036042 | 22.28s | 2.06s | -20.22s |
| [synthetic-investment-and-royalty-income-render.pdf](synthetic-investment-and-royalty-income-render.md) | bda | $0.052167 | $0.048805 | $0.012167 | -0.036638 | 26.15s | 1.59s | -24.56s |
| [synthetic-investment-and-royalty-income-scan.jpg](synthetic-investment-and-royalty-income-scan.md) | bda | $0.053029 | $0.049285 | $0.013029 | -0.036257 | 20.11s | 1.56s | -18.55s |
| [synthetic-public-benefits-identity-proof-state-photo-id.jpg](synthetic-public-benefits-identity-proof-state-photo-id.md) | textract | $0.040318 | $0.033854 | $0.015318 | -0.018537 | 2.15s | 2.25s | +0.10s |
| [synthetic-public-benefits-income-proof-pay-statement-photo.png](synthetic-public-benefits-income-proof-pay-statement-photo.md) | bda | $0.063589 | $0.048989 | $0.023589 | -0.025400 | 23.09s | 11.41s | -11.68s |
| [synthetic-public-benefits-income-proof-pay-statement-rendered.png](synthetic-public-benefits-income-proof-pay-statement-rendered.md) | bda | $0.063492 | $0.048892 | $0.023492 | -0.025401 | 23.86s | 11.25s | -12.61s |
| [synthetic-public-benefits-income-proof-pay-stub.jpg](synthetic-public-benefits-income-proof-pay-stub.md) | bda | $0.063462 | $0.048958 | $0.023462 | -0.025496 | 23.66s | 11.00s | -12.66s |
| [synthetic-shelter-shelter-verification-render.pdf](synthetic-shelter-shelter-verification-render.md) | bda | $0.051978 | $0.048818 | $0.011978 | -0.036839 | 28.07s | 1.98s | -26.09s |
| [synthetic-shelter-shelter-verification-scan.jpg](synthetic-shelter-shelter-verification-scan.md) | bda | $0.054228 | $0.049253 | $0.014228 | -0.035026 | 17.52s | 2.40s | -15.12s |
| [synthetic-snap-income-proof-employment-wage-verification-letter-photo.png](synthetic-snap-income-proof-employment-wage-verification-letter-photo.md) | bda | $0.051788 | $0.048996 | $0.011788 | -0.037208 | 18.12s | 1.15s | -16.97s |
| [synthetic-snap-income-proof-employment-wage-verification-letter-rendered.png](synthetic-snap-income-proof-employment-wage-verification-letter-rendered.md) | bda | $0.051729 | $0.048924 | $0.011729 | -0.037195 | 19.43s | 1.00s | -18.43s |

