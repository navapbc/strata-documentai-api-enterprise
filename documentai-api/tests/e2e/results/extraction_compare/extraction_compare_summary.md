# Extraction Compare Results

_Run: 2026-09-26 22:50 UTC_

**Avg Durations**
- bda: 24.84s
- llm: 4.55s
- textract: 2.15s


**Total Cost by Model**
- bda: $1.400000
- textract: $0.025000
- us.amazon.nova-lite-v1:0: $0.002914
- us.amazon.nova-pro-v1:0: $0.554532
- **total: $1.982446**


**BDA vs LLM Cost (docs where primary=bda)**
- shared (preclassification): $0.317988
- bda extraction total: $1.400000
- LLM extraction total: $0.224141


**Textract vs LLM Cost (docs where primary=textract)**
- shared (preclassification): $0.008854
- textract extraction total: $0.025000
- LLM extraction total: $0.006463


| Document | Method | Total Cost | Primary Cost | LLM Cost | Cost Delta | Primary Duration | LLM Duration | Duration Delta |
|---|---|---|---|---|---|---|---|---|
| [synthetic-assets-bank-statement-render-spanish.png](synthetic-assets-bank-statement-render-spanish.md) | bda | $0.059328 | $0.049330 | $0.009998 | -0.039333 | 31.25s | 17.03s | -14.22s |
| [synthetic-assets-bank-statement-render.pdf](synthetic-assets-bank-statement-render.md) | bda | $0.054264 | $0.048760 | $0.005504 | -0.043256 | 22.80s | 3.42s | -19.39s |
| [synthetic-assets-bank-statement-scan.jpg](synthetic-assets-bank-statement-scan.md) | bda | $0.058475 | $0.049257 | $0.009218 | -0.040038 | 25.03s | 12.62s | -12.41s |
| [synthetic-assets-life-insurance-policy-render.pdf](synthetic-assets-life-insurance-policy-render.md) | bda | $0.052354 | $0.048805 | $0.003549 | -0.045256 | 22.91s | 1.53s | -21.38s |
| [synthetic-assets-life-insurance-policy-scan.jpg](synthetic-assets-life-insurance-policy-scan.md) | bda | $0.053170 | $0.049260 | $0.003910 | -0.045349 | 22.94s | 4.47s | -18.47s |
| [synthetic-assets-trust-funds-investment-accounts-render-spanish.png](synthetic-assets-trust-funds-investment-accounts-render-spanish.md) | bda | $0.053891 | $0.049295 | $0.004596 | -0.044699 | 23.44s | 1.77s | -21.67s |
| [synthetic-assets-trust-funds-investment-accounts-render.pdf](synthetic-assets-trust-funds-investment-accounts-render.md) | bda | $0.052735 | $0.048789 | $0.003946 | -0.044842 | 22.01s | 5.14s | -16.87s |
| [synthetic-assets-trust-funds-investment-accounts-scan.jpg](synthetic-assets-trust-funds-investment-accounts-scan.md) | bda | $0.053724 | $0.049279 | $0.004446 | -0.044833 | 23.14s | 2.14s | -21.00s |
| [synthetic-expense-burial-scan-corner-torn.jpg](synthetic-expense-burial-scan-corner-torn.md) | bda | $0.053559 | $0.049266 | $0.004293 | -0.044973 | 21.61s | 2.02s | -19.59s |
| [synthetic-expense-child-support-rendered.pdf](synthetic-expense-child-support-rendered.md) | bda | $0.053294 | $0.048770 | $0.004525 | -0.044245 | 25.94s | 1.20s | -24.75s |
| [synthetic-expense-child-support-scan.jpg](synthetic-expense-child-support-scan.md) | bda | $0.055496 | $0.049304 | $0.006191 | -0.043113 | 34.84s | 2.17s | -32.67s |
| [synthetic-expense-child-support-spanish-picture.png](synthetic-expense-child-support-spanish-picture.md) | bda | $0.055615 | $0.049308 | $0.006307 | -0.043001 | 27.56s | 2.03s | -25.53s |
| [synthetic-expense-dependent-care-render.pdf](synthetic-expense-dependent-care-render.md) | bda | $0.052843 | $0.048805 | $0.004038 | -0.044766 | 22.98s | 2.86s | -20.12s |
| [synthetic-expense-dependent-care-scan.png](synthetic-expense-dependent-care-scan.md) | bda | $0.053981 | $0.049266 | $0.004714 | -0.044552 | 26.02s | 2.72s | -23.30s |
| [synthetic-expense-utility-cable-bill-render-spanish.png](synthetic-expense-utility-cable-bill-render-spanish.md) | bda | $0.055802 | $0.049276 | $0.006526 | -0.042749 | 37.31s | 3.62s | -33.69s |
| [synthetic-expense-utility-cable-bill-render.pdf](synthetic-expense-utility-cable-bill-render.md) | bda | $0.053272 | $0.048776 | $0.004496 | -0.044280 | 25.90s | 1.95s | -23.95s |
| [synthetic-expense-utility-electric-bill-render-spanish.png](synthetic-expense-utility-electric-bill-render-spanish.md) | bda | $0.059339 | $0.049263 | $0.010076 | -0.039187 | 23.99s | 8.13s | -15.86s |
| [synthetic-expense-utility-electric-bill-render.pdf](synthetic-expense-utility-electric-bill-render.md) | bda | $0.059695 | $0.048802 | $0.010894 | -0.037908 | 24.27s | 16.94s | -7.33s |
| [synthetic-expense-utility-electric-bill-scan.jpg](synthetic-expense-utility-electric-bill-scan.md) | bda | $0.059051 | $0.049289 | $0.009762 | -0.039526 | 33.29s | 7.51s | -25.78s |
| [synthetic-expense-utility-water-sewer-bill-render-spanish.png](synthetic-expense-utility-water-sewer-bill-render-spanish.md) | bda | $0.057964 | $0.049273 | $0.008690 | -0.040583 | 28.78s | 3.81s | -24.98s |
| [synthetic-expense-utility-water-sewer-bill-render.pdf](synthetic-expense-utility-water-sewer-bill-render.md) | bda | $0.056446 | $0.048792 | $0.007654 | -0.041138 | 21.82s | 3.12s | -18.70s |
| [synthetic-expense-utility-water-sewer-bill-scan.jpg](synthetic-expense-utility-water-sewer-bill-scan.md) | bda | $0.057324 | $0.049334 | $0.007990 | -0.041343 | 24.66s | 3.70s | -20.96s |
| [synthetic-insurance-health-insurance-premium-render-spanish.png](synthetic-insurance-health-insurance-premium-render-spanish.md) | bda | $0.054256 | $0.049353 | $0.004903 | -0.044449 | 25.94s | 1.94s | -24.00s |
| [synthetic-insurance-health-insurance-premium-render.pdf](synthetic-insurance-health-insurance-premium-render.md) | bda | $0.053409 | $0.048802 | $0.004607 | -0.044194 | 27.83s | 2.03s | -25.80s |
| [synthetic-insurance-health-insurance-premium-scan.jpg](synthetic-insurance-health-insurance-premium-scan.md) | bda | $0.054143 | $0.049337 | $0.004806 | -0.044530 | 21.01s | 2.14s | -18.87s |
| [synthetic-investment-and-royalty-income-render-spanish.png](synthetic-investment-and-royalty-income-render-spanish.md) | bda | $0.053237 | $0.049279 | $0.003958 | -0.045321 | 22.28s | 2.06s | -20.22s |
| [synthetic-investment-and-royalty-income-render.pdf](synthetic-investment-and-royalty-income-render.md) | bda | $0.052167 | $0.048805 | $0.003362 | -0.045442 | 26.15s | 1.59s | -24.56s |
| [synthetic-investment-and-royalty-income-scan.jpg](synthetic-investment-and-royalty-income-scan.md) | bda | $0.053029 | $0.049285 | $0.003743 | -0.045542 | 20.11s | 1.56s | -18.55s |
| [synthetic-public-benefits-identity-proof-state-photo-id.jpg](synthetic-public-benefits-identity-proof-state-photo-id.md) | textract | $0.040318 | $0.033854 | $0.006463 | -0.027391 | - | 2.25s | +0.10s |
| [synthetic-public-benefits-income-proof-pay-statement-photo.png](synthetic-public-benefits-income-proof-pay-statement-photo.md) | bda | $0.063589 | $0.048989 | $0.014600 | -0.034389 | 23.09s | 11.41s | -11.68s |
| [synthetic-public-benefits-income-proof-pay-statement-rendered.png](synthetic-public-benefits-income-proof-pay-statement-rendered.md) | bda | $0.063492 | $0.048892 | $0.014599 | -0.034293 | 23.86s | 11.25s | -12.61s |
| [synthetic-public-benefits-income-proof-pay-stub.jpg](synthetic-public-benefits-income-proof-pay-stub.md) | bda | $0.063462 | $0.048958 | $0.014504 | -0.034454 | 23.66s | 11.00s | -12.66s |
| [synthetic-shelter-shelter-verification-render.pdf](synthetic-shelter-shelter-verification-render.md) | bda | $0.051978 | $0.048818 | $0.003161 | -0.045657 | 28.07s | 1.98s | -26.09s |
| [synthetic-shelter-shelter-verification-scan.jpg](synthetic-shelter-shelter-verification-scan.md) | bda | $0.054228 | $0.049253 | $0.004974 | -0.044279 | 17.52s | 2.40s | -15.12s |
| [synthetic-snap-income-proof-employment-wage-verification-letter-photo.png](synthetic-snap-income-proof-employment-wage-verification-letter-photo.md) | bda | $0.051788 | $0.048996 | $0.002792 | -0.046204 | 18.12s | 1.15s | -16.97s |
| [synthetic-snap-income-proof-employment-wage-verification-letter-rendered.png](synthetic-snap-income-proof-employment-wage-verification-letter-rendered.md) | bda | $0.051729 | $0.048924 | $0.002805 | -0.046120 | 19.43s | 1.00s | -18.43s |

