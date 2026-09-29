# Extraction Compare Results

_Run: 2026-09-29 20:03 UTC_

## Avg Durations
- bda: 24.65s
- ocr-mapping: 4.22s
- textract: 2.50s


## Total Cost by Model
- us.amazon.nova-lite-v1:0: $0.003037
- us.amazon.nova-pro-v1:0: $0.569923
- **total: $0.572960**


## Primary Extraction Method vs. LLM via Textract
### Cost & Duration 
| Primary Method | Shared (preclass) | Primary Total | LLM Total | LLM vs Primary | Median Primary Duration | Median LLM Duration | LLM vs Primary |
|---|---|---|---|---|---|---|---|
| bda | $0.327435 | $1.440000 | $0.230058 | 6.3x cheaper | 24.42s | 2.68s | 9.1x faster |
| textract | $0.008867 | $0.025000 | $0.006600 | 3.8x cheaper | 2.50s | 2.75s | 0.9x slower |


### Accuracy
| Metric | BDA vs LLM | TEXTRACT vs LLM |
|---|---|---|
| Equivalent Match | 76% / 82% | 92% / 100% |
| Close Match | 77% / 82% | 92% / 100% |


## Document Summary

| Document | Method | Total Cost | Primary Cost | LLM Cost | Cost Delta | Primary Duration | LLM Duration | Duration Delta | Primary Accuracy | LLM Accuracy |
|---|---|---|---|---|---|---|---|---|---|---|
| [synthetic-assets-bank-statement-render-spanish.png](synthetic-assets-bank-statement-render-spanish.md) | bda | $0.057429 | $0.049343 | $0.017429 | -0.031914 | 24.62s | 5.49s | -19.13s | 47% | 73% |
| [synthetic-assets-bank-statement-render.pdf](synthetic-assets-bank-statement-render.md) | bda | $0.053778 | $0.048763 | $0.013778 | -0.034986 | 21.67s | 2.63s | -19.04s | 75% | 100% |
| [synthetic-assets-bank-statement-scan.jpg](synthetic-assets-bank-statement-scan.md) | bda | $0.056640 | $0.049266 | $0.016640 | -0.032626 | 23.35s | 4.78s | -18.57s | 53% | 73% |
| [synthetic-assets-life-insurance-policy-render.pdf](synthetic-assets-life-insurance-policy-render.md) | bda | $0.052542 | $0.048843 | $0.012542 | -0.036302 | 23.03s | 1.88s | -21.15s | 100% | 100% |
| [synthetic-assets-life-insurance-policy-scan.jpg](synthetic-assets-life-insurance-policy-scan.md) | bda | $0.053329 | $0.049282 | $0.013329 | -0.035953 | 19.72s | 1.78s | -17.94s | 100% | 100% |
| [synthetic-assets-trust-funds-investment-accounts-render-spanish.png](synthetic-assets-trust-funds-investment-accounts-render-spanish.md) | bda | $0.054031 | $0.049298 | $0.014031 | -0.035267 | 25.49s | 3.25s | -22.24s | 90% | 90% |
| [synthetic-assets-trust-funds-investment-accounts-render.pdf](synthetic-assets-trust-funds-investment-accounts-render.md) | bda | $0.052885 | $0.048802 | $0.012885 | -0.035917 | 20.26s | 5.34s | -14.92s | 70% | 90% |
| [synthetic-assets-trust-funds-investment-accounts-scan.jpg](synthetic-assets-trust-funds-investment-accounts-scan.md) | bda | $0.053861 | $0.049276 | $0.013861 | -0.035414 | 20.18s | 2.14s | -18.04s | 90% | 100% |
| [synthetic-expense-burial-scan-corner-torn.jpg](synthetic-expense-burial-scan-corner-torn.md) | bda | $0.053773 | $0.049292 | $0.013773 | -0.035519 | 20.37s | 2.05s | -18.32s | 67% | 78% |
| [synthetic-expense-child-support-rendered.pdf](synthetic-expense-child-support-rendered.md) | bda | $0.053697 | $0.048792 | $0.013697 | -0.035095 | 27.89s | 1.83s | -26.06s | 100% | 83% |
| [synthetic-expense-child-support-scan.jpg](synthetic-expense-child-support-scan.md) | bda | $0.055556 | $0.049279 | $0.015556 | -0.033723 | 40.51s | 2.73s | -37.78s | 100% | 93% |
| [synthetic-expense-child-support-spanish-picture.png](synthetic-expense-child-support-spanish-picture.md) | bda | $0.055755 | $0.049317 | $0.015755 | -0.033562 | 31.80s | 2.57s | -29.23s | 77% | 92% |
| [synthetic-expense-dependent-care-render.pdf](synthetic-expense-dependent-care-render.md) | bda | $0.052986 | $0.048798 | $0.012986 | -0.035812 | 22.33s | 2.37s | -19.96s | 91% | 100% |
| [synthetic-expense-dependent-care-scan.png](synthetic-expense-dependent-care-scan.md) | bda | $0.053906 | $0.049266 | $0.013906 | -0.035360 | 27.06s | 2.64s | -24.42s | 82% | 100% |
| [synthetic-expense-utility-cable-bill-render-spanish.png](synthetic-expense-utility-cable-bill-render-spanish.md) | bda | $0.055952 | $0.049269 | $0.015952 | -0.033318 | 25.13s | 5.54s | -19.59s | 70% | 50% |
| [synthetic-expense-utility-cable-bill-render.pdf](synthetic-expense-utility-cable-bill-render.md) | bda | $0.054110 | $0.048802 | $0.014110 | -0.034692 | 33.43s | 3.47s | -29.96s | 60% | 90% |
| [synthetic-expense-utility-electric-bill-render-spanish.png](synthetic-expense-utility-electric-bill-render-spanish.md) | bda | $0.060122 | $0.049276 | $0.020122 | -0.029154 | 25.13s | 10.86s | -14.27s | 44% | 88% |
| [synthetic-expense-utility-electric-bill-render.pdf](synthetic-expense-utility-electric-bill-render.md) | bda | $0.057605 | $0.048782 | $0.017605 | -0.031178 | 28.97s | 6.49s | -22.48s | 50% | 58% |
| [synthetic-expense-utility-electric-bill-scan.jpg](synthetic-expense-utility-electric-bill-scan.md) | bda | $0.059537 | $0.049273 | $0.019537 | -0.029736 | 30.32s | 9.48s | -20.84s | 44% | 68% |
| [synthetic-expense-utility-water-sewer-bill-render-spanish.png](synthetic-expense-utility-water-sewer-bill-render-spanish.md) | bda | $0.058321 | $0.049330 | $0.018321 | -0.031010 | 27.91s | 5.55s | -22.36s | 81% | 95% |
| [synthetic-expense-utility-water-sewer-bill-render.pdf](synthetic-expense-utility-water-sewer-bill-render.md) | bda | $0.056854 | $0.048830 | $0.016854 | -0.031976 | 22.93s | 5.67s | -17.26s | 84% | 89% |
| [synthetic-expense-utility-water-sewer-bill-scan.jpg](synthetic-expense-utility-water-sewer-bill-scan.md) | bda | $0.057844 | $0.049314 | $0.017844 | -0.031470 | 24.22s | 4.71s | -19.51s | 90% | 100% |
| [synthetic-insurance-health-insurance-premium-render-spanish.png](synthetic-insurance-health-insurance-premium-render-spanish.md) | bda | $0.054293 | $0.049301 | $0.014293 | -0.035008 | 27.96s | 2.29s | -25.67s | 100% | 73% |
| [synthetic-insurance-health-insurance-premium-render.pdf](synthetic-insurance-health-insurance-premium-render.md) | bda | $0.053469 | $0.048811 | $0.013469 | -0.035342 | 25.60s | 1.90s | -23.70s | 100% | 91% |
| [synthetic-insurance-health-insurance-premium-scan.jpg](synthetic-insurance-health-insurance-premium-scan.md) | bda | $0.054261 | $0.049269 | $0.014261 | -0.035009 | 20.37s | 2.09s | -18.28s | 100% | 91% |
| [synthetic-investment-and-royalty-income-render-spanish.png](synthetic-investment-and-royalty-income-render-spanish.md) | bda | $0.053173 | $0.049298 | $0.013173 | -0.036126 | 20.63s | 1.99s | -18.64s | 50% | 58% |
| [synthetic-investment-and-royalty-income-render.pdf](synthetic-investment-and-royalty-income-render.md) | bda | $0.052314 | $0.048827 | $0.012314 | -0.036514 | 19.11s | 2.14s | -16.97s | 33% | 100% |
| [synthetic-investment-and-royalty-income-scan.jpg](synthetic-investment-and-royalty-income-scan.md) | bda | $0.053185 | $0.049308 | $0.013185 | -0.036123 | 22.25s | 1.99s | -20.27s | 42% | 67% |
| [synthetic-public-benefits-identity-proof-state-photo-id.jpg](synthetic-public-benefits-identity-proof-state-photo-id.md) | textract | $0.040467 | $0.033867 | $0.015467 | -0.018400 | 2.50s | 2.75s | +0.25s | 92% | 100% |
| [synthetic-public-benefits-income-proof-pay-statement-photo.png](synthetic-public-benefits-income-proof-pay-statement-photo.md) | bda | $0.063732 | $0.048983 | $0.023732 | -0.025250 | 25.95s | 12.08s | -13.87s | 83% | 91% |
| [synthetic-public-benefits-income-proof-pay-statement-rendered.png](synthetic-public-benefits-income-proof-pay-statement-rendered.md) | bda | $0.063638 | $0.048889 | $0.023638 | -0.025251 | 25.04s | 12.53s | -12.51s | 83% | 91% |
| [synthetic-public-benefits-income-proof-pay-stub.jpg](synthetic-public-benefits-income-proof-pay-stub.md) | bda | $0.063580 | $0.048942 | $0.023580 | -0.025362 | 24.15s | 11.85s | -12.30s | 79% | 86% |
| [synthetic-shelter-shelter-verification-render-spanish.png](synthetic-shelter-shelter-verification-render-spanish.md) | bda | $0.055189 | $0.049269 | $0.015189 | -0.034081 | 27.81s | 3.34s | -24.47s | 71% | 0% |
| [synthetic-shelter-shelter-verification-render.pdf](synthetic-shelter-shelter-verification-render.md) | bda | $0.052115 | $0.048818 | $0.012115 | -0.036702 | 29.17s | 2.71s | -26.46s | 100% | 71% |
| [synthetic-shelter-shelter-verification-scan.jpg](synthetic-shelter-shelter-verification-scan.md) | bda | $0.054205 | $0.049266 | $0.014205 | -0.035062 | 18.18s | 2.43s | -15.75s | 80% | 60% |
| [synthetic-snap-income-proof-employment-wage-verification-letter-photo.png](synthetic-snap-income-proof-employment-wage-verification-letter-photo.md) | bda | $0.051937 | $0.049008 | $0.011937 | -0.037071 | 18.45s | 1.45s | -17.00s | 100% | 86% |
| [synthetic-snap-income-proof-employment-wage-verification-letter-rendered.png](synthetic-snap-income-proof-employment-wage-verification-letter-rendered.md) | bda | $0.051892 | $0.048950 | $0.011892 | -0.037058 | 16.33s | 1.42s | -14.91s | 100% | 86% |

