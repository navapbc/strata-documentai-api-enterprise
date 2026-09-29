# Extraction Compare Results

_Run: 2026-09-29 16:14 UTC_

## Avg Durations
- bda: 25.13s
- llm: 5.48s
- textract: 2.54s


## Total Cost by Model
- us.amazon.nova-lite-v1:0: $0.003313
- us.amazon.nova-pro-v1:0: $0.564801
- **total: $0.568113**


## Primary Extraction Method vs. LLM via Textract
### Cost & Duration 
| Primary Method | Shared (preclass) | Primary Total | LLM Total | LLM vs Primary | Median Primary Duration | Median LLM Duration | LLM vs Primary |
|---|---|---|---|---|---|---|---|
| bda | $0.327346 | $1.440000 | $0.225319 | 6.4x cheaper | 25.55s | 4.30s | 5.9x faster |
| textract | $0.008848 | $0.025000 | $0.006600 | 3.8x cheaper | 2.54s | 3.97s | 0.6x slower |


### Accuracy
| Metric | BDA vs LLM | TEXTRACT vs LLM |
|---|---|---|
| Equivalent Match | 76% / 84% | 92% / 100% |
| Close Match | 77% / 85% | 92% / 100% |


## Document Summary

| Document | Method | Total Cost | Primary Cost | LLM Cost | Cost Delta | Primary Duration | LLM Duration | Duration Delta | Primary Accuracy | LLM Accuracy |
|---|---|---|---|---|---|---|---|---|---|---|
| [synthetic-assets-bank-statement-render-spanish.png](synthetic-assets-bank-statement-render-spanish.md) | bda | $0.056716 | $0.049276 | $0.016716 | -0.032560 | 26.53s | 16.36s | -10.17s | 47% | 73% |
| [synthetic-assets-bank-statement-render.pdf](synthetic-assets-bank-statement-render.md) | bda | $0.054171 | $0.048782 | $0.014171 | -0.034611 | 25.63s | 8.02s | -17.61s | 75% | 100% |
| [synthetic-assets-bank-statement-scan.jpg](synthetic-assets-bank-statement-scan.md) | bda | $0.056809 | $0.049260 | $0.016809 | -0.032450 | 27.00s | 9.93s | -17.07s | 53% | 73% |
| [synthetic-assets-life-insurance-policy-render.pdf](synthetic-assets-life-insurance-policy-render.md) | bda | $0.052532 | $0.048834 | $0.012532 | -0.036302 | 21.20s | 1.82s | -19.38s | 100% | 100% |
| [synthetic-assets-life-insurance-policy-scan.jpg](synthetic-assets-life-insurance-policy-scan.md) | bda | $0.053352 | $0.049305 | $0.013352 | -0.035953 | 26.18s | 5.66s | -20.52s | 100% | 100% |
| [synthetic-assets-trust-funds-investment-accounts-render-spanish.png](synthetic-assets-trust-funds-investment-accounts-render-spanish.md) | bda | $0.054009 | $0.049276 | $0.014009 | -0.035267 | 22.88s | 5.86s | -17.02s | 90% | 90% |
| [synthetic-assets-trust-funds-investment-accounts-render.pdf](synthetic-assets-trust-funds-investment-accounts-render.md) | bda | $0.052862 | $0.048779 | $0.012862 | -0.035917 | 25.23s | 11.91s | -13.32s | 70% | 90% |
| [synthetic-assets-trust-funds-investment-accounts-scan.jpg](synthetic-assets-trust-funds-investment-accounts-scan.md) | bda | $0.053861 | $0.049285 | $0.013861 | -0.035424 | 33.93s | 4.27s | -29.66s | 90% | 100% |
| [synthetic-expense-burial-scan-corner-torn.jpg](synthetic-expense-burial-scan-corner-torn.md) | bda | $0.053430 | $0.049260 | $0.013430 | -0.035830 | 20.16s | 2.19s | -17.97s | 67% | 78% |
| [synthetic-expense-child-support-rendered.pdf](synthetic-expense-child-support-rendered.md) | bda | $0.053662 | $0.048779 | $0.013662 | -0.035118 | 34.81s | 2.52s | -32.29s | 100% | 83% |
| [synthetic-expense-child-support-scan.jpg](synthetic-expense-child-support-scan.md) | bda | $0.055729 | $0.049305 | $0.015729 | -0.033576 | 29.51s | 3.63s | -25.88s | 100% | 100% |
| [synthetic-expense-child-support-spanish-picture.png](synthetic-expense-child-support-spanish-picture.md) | bda | $0.055761 | $0.049324 | $0.015761 | -0.033562 | 28.03s | 2.86s | -25.17s | 77% | 92% |
| [synthetic-expense-dependent-care-render.pdf](synthetic-expense-dependent-care-render.md) | bda | $0.052964 | $0.048776 | $0.012964 | -0.035812 | 26.67s | 2.29s | -24.38s | 91% | 100% |
| [synthetic-expense-dependent-care-scan.png](synthetic-expense-dependent-care-scan.md) | bda | $0.053865 | $0.049273 | $0.013865 | -0.035408 | 27.98s | 2.33s | -25.65s | 82% | 82% |
| [synthetic-expense-utility-cable-bill-render-spanish.png](synthetic-expense-utility-cable-bill-render-spanish.md) | bda | $0.056064 | $0.049301 | $0.016064 | -0.033238 | 25.46s | 7.66s | -17.80s | 70% | 50% |
| [synthetic-expense-utility-cable-bill-render.pdf](synthetic-expense-utility-cable-bill-render.md) | bda | $0.054113 | $0.048805 | $0.014113 | -0.034692 | 24.85s | 4.34s | -20.51s | 60% | 90% |
| [synthetic-expense-utility-electric-bill-render-spanish.png](synthetic-expense-utility-electric-bill-render-spanish.md) | bda | $0.059901 | $0.049263 | $0.019901 | -0.029362 | 24.20s | 11.02s | -13.18s | 44% | 68% |
| [synthetic-expense-utility-electric-bill-render.pdf](synthetic-expense-utility-electric-bill-render.md) | bda | $0.058648 | $0.048786 | $0.018648 | -0.030138 | 27.59s | 9.69s | -17.91s | 50% | 75% |
| [synthetic-expense-utility-electric-bill-scan.jpg](synthetic-expense-utility-electric-bill-scan.md) | bda | $0.059562 | $0.049298 | $0.019562 | -0.029736 | 25.32s | 8.64s | -16.68s | 44% | 68% |
| [synthetic-expense-utility-water-sewer-bill-render-spanish.png](synthetic-expense-utility-water-sewer-bill-render-spanish.md) | bda | $0.058212 | $0.049285 | $0.018212 | -0.031074 | 28.29s | 5.25s | -23.04s | 81% | 95% |
| [synthetic-expense-utility-water-sewer-bill-render.pdf](synthetic-expense-utility-water-sewer-bill-render.md) | bda | $0.056816 | $0.048805 | $0.016816 | -0.031989 | 21.70s | 5.15s | -16.55s | 84% | 89% |
| [synthetic-expense-utility-water-sewer-bill-scan.jpg](synthetic-expense-utility-water-sewer-bill-scan.md) | bda | $0.057809 | $0.049276 | $0.017809 | -0.031466 | 26.04s | 4.45s | -21.59s | 90% | 100% |
| [synthetic-insurance-health-insurance-premium-render-spanish.png](synthetic-insurance-health-insurance-premium-render-spanish.md) | bda | $0.054329 | $0.049289 | $0.014329 | -0.034960 | 29.47s | 2.75s | -26.72s | 100% | 73% |
| [synthetic-insurance-health-insurance-premium-render.pdf](synthetic-insurance-health-insurance-premium-render.md) | bda | $0.053453 | $0.048795 | $0.013453 | -0.035342 | 28.50s | 2.73s | -25.77s | 100% | 91% |
| [synthetic-insurance-health-insurance-premium-scan.jpg](synthetic-insurance-health-insurance-premium-scan.md) | bda | $0.054206 | $0.049292 | $0.014206 | -0.035086 | 19.81s | 3.02s | -16.79s | 100% | 91% |
| [synthetic-investment-and-royalty-income-render-spanish.png](synthetic-investment-and-royalty-income-render-spanish.md) | bda | $0.053185 | $0.049311 | $0.013185 | -0.036126 | 20.12s | 2.57s | -17.55s | 50% | 58% |
| [synthetic-investment-and-royalty-income-render.pdf](synthetic-investment-and-royalty-income-render.md) | bda | $0.052298 | $0.048814 | $0.012298 | -0.036517 | 20.77s | 2.51s | -18.26s | 33% | 100% |
| [synthetic-investment-and-royalty-income-scan.jpg](synthetic-investment-and-royalty-income-scan.md) | bda | $0.053162 | $0.049285 | $0.013162 | -0.036123 | 24.82s | 2.32s | -22.50s | 42% | 67% |
| [synthetic-public-benefits-identity-proof-state-photo-id.jpg](synthetic-public-benefits-identity-proof-state-photo-id.md) | textract | $0.040448 | $0.033848 | $0.015448 | -0.018400 | 2.54s | 3.97s | +1.43s | 92% | 100% |
| [synthetic-public-benefits-income-proof-pay-statement-photo.png](synthetic-public-benefits-income-proof-pay-statement-photo.md) | bda | $0.063758 | $0.049008 | $0.023758 | -0.025250 | 27.74s | 11.81s | -15.93s | 83% | 91% |
| [synthetic-public-benefits-income-proof-pay-statement-rendered.png](synthetic-public-benefits-income-proof-pay-statement-rendered.md) | bda | $0.063629 | $0.048893 | $0.023629 | -0.025264 | 24.81s | 11.33s | -13.48s | 83% | 91% |
| [synthetic-public-benefits-income-proof-pay-stub.jpg](synthetic-public-benefits-income-proof-pay-stub.md) | bda | $0.063599 | $0.048958 | $0.023599 | -0.025359 | 22.45s | 11.13s | -11.32s | 79% | 90% |
| [synthetic-shelter-shelter-verification-render-spanish.png](synthetic-shelter-shelter-verification-render-spanish.md) | bda | $0.049602 | $0.049327 | $0.009602 | -0.039725 | 25.80s | 2.49s | -23.31s | 71% | 57% |
| [synthetic-shelter-shelter-verification-render.pdf](synthetic-shelter-shelter-verification-render.md) | bda | $0.052387 | $0.048827 | $0.012387 | -0.036440 | 26.81s | 2.45s | -24.36s | 100% | 86% |
| [synthetic-shelter-shelter-verification-scan.jpg](synthetic-shelter-shelter-verification-scan.md) | bda | $0.054406 | $0.049295 | $0.014406 | -0.034889 | 17.70s | 4.36s | -13.34s | 80% | 90% |
| [synthetic-snap-income-proof-employment-wage-verification-letter-photo.png](synthetic-snap-income-proof-employment-wage-verification-letter-photo.md) | bda | $0.051953 | $0.049012 | $0.011953 | -0.037058 | 19.64s | 2.13s | -17.51s | 100% | 86% |
| [synthetic-snap-income-proof-employment-wage-verification-letter-rendered.png](synthetic-snap-income-proof-employment-wage-verification-letter-rendered.md) | bda | $0.051850 | $0.048909 | $0.011850 | -0.037058 | 16.95s | 1.43s | -15.52s | 100% | 86% |

