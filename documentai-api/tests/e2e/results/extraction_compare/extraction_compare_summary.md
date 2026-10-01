# Extraction Compare Results

_Run: 2026-10-01 01:41 UTC_

## Avg Durations
- bda: 26.23s
- ocr-mapping: 4.65s
- textract: 2.23s


## Total Cost by Model
- us.amazon.nova-lite-v1:0: $0.003038
- us.amazon.nova-pro-v1:0: $0.569715
- **total: $0.572753**


## Primary Extraction Method vs. LLM via Textract
### Cost & Duration 
| Primary Method | Shared (preclass) | Primary Total | LLM Total | Cost Ratio | Median Primary Duration | Median LLM Duration | Speed Ratio |
|---|---|---|---|---|---|---|---|
| bda | $0.327346 | $1.440000 | $0.229939 | 6.3x cheaper | 26.04s | 2.54s | 10.3x faster |
| textract | $0.008867 | $0.025000 | $0.006600 | 3.8x cheaper | 2.23s | 2.34s | 1.0x slower |


### Accuracy
| Primary Method | Primary Match (Equiv.) | LLM Match (Equiv.) | Primary Match (Equiv+Approx.) | LLM Match (Equiv+Approx.) | Primary Bounding Box Match | LLM Bounding Box Match |
|---|---|---|---|---|---|---|
| bda | 78% | 84% | 80% | 84% | 156/267 (58%) | 180/301 (60%) |
| textract | 92% | 100% | 92% | 100% | 7/9 (78%) | 7/10 (70%) |


## Document Summary

| Document | Method | Total Cost | Primary Cost | LLM Cost | Cost Delta | Primary Duration | LLM Duration | Duration Delta | Primary Match Rate (Equiv+Approx.) | LLM Match Rate (Equiv+Approx.) | Match Rate Delta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| [synthetic-assets-bank-statement-render-spanish.png](synthetic-assets-bank-statement-render-spanish.md) | bda | $0.057292 | $0.049292 | $0.017292 | -0.032000 | 23.59s | 7.92s | -15.67s | 47% | 73% | +26.7% |
| [synthetic-assets-bank-statement-render.pdf](synthetic-assets-bank-statement-render.md) | bda | $0.053781 | $0.048766 | $0.013781 | -0.034986 | 22.38s | 1.86s | -20.52s | 75% | 100% | +25.0% |
| [synthetic-assets-bank-statement-scan.jpg](synthetic-assets-bank-statement-scan.md) | bda | $0.056851 | $0.049260 | $0.016851 | -0.032409 | 26.77s | 7.27s | -19.50s | 53% | 73% | +20.0% |
| [synthetic-assets-life-insurance-policy-render.pdf](synthetic-assets-life-insurance-policy-render.md) | bda | $0.052526 | $0.048827 | $0.012526 | -0.036302 | 22.86s | 1.34s | -21.52s | 100% | 100% | 0% |
| [synthetic-assets-life-insurance-policy-scan.jpg](synthetic-assets-life-insurance-policy-scan.md) | bda | $0.053336 | $0.049289 | $0.013336 | -0.035953 | 24.13s | 4.62s | -19.52s | 100% | 100% | 0% |
| [synthetic-assets-trust-funds-investment-accounts-render-spanish.png](synthetic-assets-trust-funds-investment-accounts-render-spanish.md) | bda | $0.054053 | $0.049321 | $0.014053 | -0.035267 | 23.90s | 2.25s | -21.65s | 90% | 90% | 0% |
| [synthetic-assets-trust-funds-investment-accounts-render.pdf](synthetic-assets-trust-funds-investment-accounts-render.md) | bda | $0.052898 | $0.048814 | $0.012898 | -0.035917 | 25.57s | 5.22s | -20.35s | 70% | 90% | +20.0% |
| [synthetic-assets-trust-funds-investment-accounts-scan.jpg](synthetic-assets-trust-funds-investment-accounts-scan.md) | bda | $0.053858 | $0.049276 | $0.013858 | -0.035418 | 23.82s | 2.00s | -21.82s | 90% | 100% | +10.0% |
| [synthetic-expense-burial-scan-corner-torn.jpg](synthetic-expense-burial-scan-corner-torn.md) | bda | $0.053737 | $0.049311 | $0.013737 | -0.035574 | 26.36s | 1.96s | -24.40s | 67% | 67% | 0% |
| [synthetic-expense-child-support-rendered.pdf](synthetic-expense-child-support-rendered.md) | bda | $0.054538 | $0.048776 | $0.014538 | -0.034238 | 26.30s | 2.74s | -23.56s | 100% | 100% | 0% |
| [synthetic-expense-child-support-scan.jpg](synthetic-expense-child-support-scan.md) | bda | $0.055585 | $0.049308 | $0.015585 | -0.033723 | 43.82s | 2.60s | -41.22s | 100% | 93% | -7.1% |
| [synthetic-expense-child-support-spanish-picture.png](synthetic-expense-child-support-spanish-picture.md) | bda | $0.055745 | $0.049308 | $0.015745 | -0.033562 | 31.07s | 2.77s | -28.30s | 92% | 92% | 0% |
| [synthetic-expense-dependent-care-render.pdf](synthetic-expense-dependent-care-render.md) | bda | $0.053002 | $0.048814 | $0.013002 | -0.035812 | 22.55s | 2.12s | -20.43s | 91% | 100% | +9.1% |
| [synthetic-expense-dependent-care-scan.png](synthetic-expense-dependent-care-scan.md) | bda | $0.054009 | $0.049308 | $0.014009 | -0.035299 | 30.17s | 1.99s | -28.19s | 82% | 91% | +9.1% |
| [synthetic-expense-utility-cable-bill-render-spanish.png](synthetic-expense-utility-cable-bill-render-spanish.md) | bda | $0.056000 | $0.049276 | $0.016000 | -0.033276 | 26.06s | 5.05s | -21.01s | 70% | 50% | -20.0% |
| [synthetic-expense-utility-cable-bill-render.pdf](synthetic-expense-utility-cable-bill-render.md) | bda | $0.054087 | $0.048779 | $0.014087 | -0.034692 | 25.24s | 4.04s | -21.20s | 60% | 90% | +30.0% |
| [synthetic-expense-utility-electric-bill-render-spanish.png](synthetic-expense-utility-electric-bill-render-spanish.md) | bda | $0.059853 | $0.049263 | $0.019853 | -0.029410 | 24.56s | 12.42s | -12.14s | 44% | 68% | +24.0% |
| [synthetic-expense-utility-electric-bill-render.pdf](synthetic-expense-utility-electric-bill-render.md) | bda | $0.058654 | $0.048792 | $0.018654 | -0.030138 | 26.16s | 9.00s | -17.16s | 50% | 75% | +25.0% |
| [synthetic-expense-utility-electric-bill-scan.jpg](synthetic-expense-utility-electric-bill-scan.md) | bda | $0.059453 | $0.049257 | $0.019453 | -0.029803 | 26.02s | 18.01s | -8.01s | 44% | 72% | +28.0% |
| [synthetic-expense-utility-water-sewer-bill-render-spanish.png](synthetic-expense-utility-water-sewer-bill-render-spanish.md) | bda | $0.058276 | $0.049285 | $0.018276 | -0.031010 | 31.33s | 5.65s | -25.68s | 81% | 95% | +14.3% |
| [synthetic-expense-utility-water-sewer-bill-render.pdf](synthetic-expense-utility-water-sewer-bill-render.md) | bda | $0.056832 | $0.048821 | $0.016832 | -0.031989 | 27.63s | 3.42s | -24.21s | 84% | 89% | +5.3% |
| [synthetic-expense-utility-water-sewer-bill-scan.jpg](synthetic-expense-utility-water-sewer-bill-scan.md) | bda | $0.058094 | $0.049308 | $0.018094 | -0.031214 | 26.17s | 3.88s | -22.29s | 90% | 100% | +9.5% |
| [synthetic-insurance-health-insurance-premium-render-spanish.png](synthetic-insurance-health-insurance-premium-render-spanish.md) | bda | $0.054325 | $0.049285 | $0.014325 | -0.034960 | 26.67s | 2.01s | -24.66s | 100% | 73% | -27.3% |
| [synthetic-insurance-health-insurance-premium-render.pdf](synthetic-insurance-health-insurance-premium-render.md) | bda | $0.053434 | $0.048776 | $0.013434 | -0.035342 | 26.43s | 2.19s | -24.24s | 100% | 91% | -9.1% |
| [synthetic-insurance-health-insurance-premium-scan.jpg](synthetic-insurance-health-insurance-premium-scan.md) | bda | $0.054187 | $0.049269 | $0.014187 | -0.035082 | 21.64s | 2.08s | -19.56s | 100% | 91% | -9.1% |
| [synthetic-investment-and-royalty-income-render-spanish.png](synthetic-investment-and-royalty-income-render-spanish.md) | bda | $0.053153 | $0.049279 | $0.013153 | -0.036126 | 21.82s | 1.65s | -20.17s | 50% | 58% | +8.3% |
| [synthetic-investment-and-royalty-income-render.pdf](synthetic-investment-and-royalty-income-render.md) | bda | $0.052310 | $0.048779 | $0.012310 | -0.036469 | 31.51s | 1.88s | -29.63s | 100% | 100% | 0% |
| [synthetic-investment-and-royalty-income-scan.jpg](synthetic-investment-and-royalty-income-scan.md) | bda | $0.053201 | $0.049337 | $0.013201 | -0.036136 | 21.58s | 1.91s | -19.67s | 42% | 67% | +25.0% |
| [synthetic-public-benefits-identity-proof-state-photo-id.jpg](synthetic-public-benefits-identity-proof-state-photo-id.md) | textract | $0.040467 | $0.033867 | $0.015467 | -0.018400 | 2.23s | 2.34s | +0.11s | 92% | 100% | +7.7% |
| [synthetic-public-benefits-income-proof-pay-statement-photo.png](synthetic-public-benefits-income-proof-pay-statement-photo.md) | bda | $0.063736 | $0.048986 | $0.023736 | -0.025250 | 24.61s | 11.49s | -13.12s | 83% | 91% | +8.6% |
| [synthetic-public-benefits-income-proof-pay-statement-rendered.png](synthetic-public-benefits-income-proof-pay-statement-rendered.md) | bda | $0.063638 | $0.048905 | $0.023638 | -0.025267 | 26.41s | 11.35s | -15.06s | 77% | 89% | +11.4% |
| [synthetic-public-benefits-income-proof-pay-stub.jpg](synthetic-public-benefits-income-proof-pay-stub.md) | bda | $0.063605 | $0.048968 | $0.023605 | -0.025362 | 27.85s | 17.48s | -10.37s | 79% | 86% | +6.9% |
| [synthetic-shelter-shelter-verification-render-spanish.png](synthetic-shelter-shelter-verification-render-spanish.md) | bda | $0.052894 | $0.049269 | $0.012894 | -0.036375 | 43.85s | 2.08s | -41.77s | 71% | 57% | -14.3% |
| [synthetic-shelter-shelter-verification-render.pdf](synthetic-shelter-shelter-verification-render.md) | bda | $0.052125 | $0.048827 | $0.012125 | -0.036702 | 29.62s | 1.79s | -27.83s | 100% | 71% | -28.6% |
| [synthetic-shelter-shelter-verification-scan.jpg](synthetic-shelter-shelter-verification-scan.md) | bda | $0.054377 | $0.049260 | $0.014377 | -0.034882 | 19.02s | 2.47s | -16.55s | 80% | 80% | 0% |
| [synthetic-snap-income-proof-employment-wage-verification-letter-photo.png](synthetic-snap-income-proof-employment-wage-verification-letter-photo.md) | bda | $0.051969 | $0.049028 | $0.011969 | -0.037058 | 18.84s | 1.42s | -17.42s | 100% | 86% | -14.3% |
| [synthetic-snap-income-proof-employment-wage-verification-letter-rendered.png](synthetic-snap-income-proof-employment-wage-verification-letter-rendered.md) | bda | $0.051869 | $0.048928 | $0.011869 | -0.037058 | 17.80s | 1.64s | -16.16s | 100% | 86% | -14.3% |

