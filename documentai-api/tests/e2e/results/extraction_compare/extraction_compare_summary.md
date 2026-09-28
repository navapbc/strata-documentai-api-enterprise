# Extraction Compare Results

_Run: 2026-09-28 18:40 UTC_

## Avg Durations
- bda: 25.04s
- llm: 4.95s
- textract: 2.28s


## Total Cost by Model
- us.amazon.nova-lite-v1:0: $0.003037
- us.amazon.nova-pro-v1:0: $0.563982
- **total: $0.567019**


## Primary Extraction Method vs. LLM via Textract
### Cost & Duration 
| Primary Method | Shared (preclass) | Primary Total | LLM Total | LLM vs Primary | Median Primary Duration | Median LLM Duration | LLM vs Primary |
|---|---|---|---|---|---|---|---|
| bda | $0.327426 | $1.440000 | $0.224256 | 6.4x cheaper | 23.88s | 2.67s | 8.9x faster |
| textract | $0.008874 | $0.025000 | $0.006463 | 3.9x cheaper | 2.28s | 3.49s | 0.7x slower |


### Accuracy
| Primary Method | Primary Exact % | LLM Exact % | Primary Exact+Approx % | LLM Exact+Approx % |
|---|---|---|---|---|
| bda | 64% | 70% | 73% | 80% |
| textract | 92% | 100% | 92% | 100% |


## Document Summary

| Document | Method | Total Cost | Primary Cost | LLM Cost | Cost Delta | Primary Duration | LLM Duration | Duration Delta | Primary Accuracy | LLM Accuracy |
|---|---|---|---|---|---|---|---|---|---|---|
| [synthetic-assets-bank-statement-render-spanish.png](synthetic-assets-bank-statement-render-spanish.md) | bda | $0.059388 | $0.049292 | $0.019388 | -0.029904 | 30.43s | 13.87s | -16.56s | 47% | 73% |
| [synthetic-assets-bank-statement-render.pdf](synthetic-assets-bank-statement-render.md) | bda | $0.054270 | $0.048782 | $0.014270 | -0.034512 | 23.05s | 5.64s | -17.41s | 75% | 100% |
| [synthetic-assets-bank-statement-scan.jpg](synthetic-assets-bank-statement-scan.md) | bda | $0.055009 | $0.049269 | $0.015009 | -0.034261 | 21.13s | 2.72s | -18.41s | 53% | 27% |
| [synthetic-assets-life-insurance-policy-render.pdf](synthetic-assets-life-insurance-policy-render.md) | bda | $0.052395 | $0.048846 | $0.012395 | -0.036451 | 20.31s | 2.13s | -18.18s | 90% | 100% |
| [synthetic-assets-life-insurance-policy-scan.jpg](synthetic-assets-life-insurance-policy-scan.md) | bda | $0.053199 | $0.049289 | $0.013199 | -0.036090 | 23.65s | 2.11s | -21.54s | 100% | 100% |
| [synthetic-assets-trust-funds-investment-accounts-render-spanish.png](synthetic-assets-trust-funds-investment-accounts-render-spanish.md) | bda | $0.053869 | $0.049273 | $0.013869 | -0.035404 | 21.59s | 1.96s | -19.63s | 80% | 80% |
| [synthetic-assets-trust-funds-investment-accounts-render.pdf](synthetic-assets-trust-funds-investment-accounts-render.md) | bda | $0.052748 | $0.048802 | $0.012748 | -0.036054 | 20.16s | 2.62s | -17.55s | 70% | 90% |
| [synthetic-assets-trust-funds-investment-accounts-scan.jpg](synthetic-assets-trust-funds-investment-accounts-scan.md) | bda | $0.053718 | $0.049272 | $0.013718 | -0.035554 | 21.24s | 1.58s | -19.66s | 90% | 90% |
| [synthetic-expense-burial-scan-corner-torn.jpg](synthetic-expense-burial-scan-corner-torn.md) | bda | $0.053610 | $0.049292 | $0.013610 | -0.035682 | 20.05s | 2.17s | -17.88s | 67% | 78% |
| [synthetic-expense-child-support-rendered.pdf](synthetic-expense-child-support-rendered.md) | bda | $0.054376 | $0.048821 | $0.014376 | -0.034445 | 31.01s | 2.87s | -28.14s | 100% | 100% |
| [synthetic-expense-child-support-scan.jpg](synthetic-expense-child-support-scan.md) | bda | $0.055643 | $0.049327 | $0.015643 | -0.033684 | 29.80s | 3.58s | -26.22s | 100% | 93% |
| [synthetic-expense-child-support-spanish-picture.png](synthetic-expense-child-support-spanish-picture.md) | bda | $0.055833 | $0.049317 | $0.015833 | -0.033485 | 27.22s | 2.86s | -24.36s | 92% | 100% |
| [synthetic-expense-dependent-care-render.pdf](synthetic-expense-dependent-care-render.md) | bda | $0.052814 | $0.048776 | $0.012814 | -0.035962 | 23.15s | 2.48s | -20.67s | 91% | 100% |
| [synthetic-expense-dependent-care-scan.png](synthetic-expense-dependent-care-scan.md) | bda | $0.054252 | $0.049260 | $0.014252 | -0.035007 | 26.86s | 3.06s | -23.80s | 82% | 91% |
| [synthetic-expense-utility-cable-bill-render-spanish.png](synthetic-expense-utility-cable-bill-render-spanish.md) | bda | $0.054020 | $0.049330 | $0.014020 | -0.035310 | 23.20s | 2.63s | -20.57s | 30% | 10% |
| [synthetic-expense-utility-cable-bill-render.pdf](synthetic-expense-utility-cable-bill-render.md) | bda | $0.053314 | $0.048818 | $0.013314 | -0.035504 | 26.10s | 2.29s | -23.81s | 20% | 70% |
| [synthetic-expense-utility-electric-bill-render-spanish.png](synthetic-expense-utility-electric-bill-render-spanish.md) | bda | $0.059390 | $0.049276 | $0.019390 | -0.029886 | 24.12s | 8.05s | -16.07s | 32% | 44% |
| [synthetic-expense-utility-electric-bill-render.pdf](synthetic-expense-utility-electric-bill-render.md) | bda | $0.059684 | $0.048766 | $0.019684 | -0.029082 | 27.85s | 17.96s | -9.89s | 38% | 79% |
| [synthetic-expense-utility-electric-bill-scan.jpg](synthetic-expense-utility-electric-bill-scan.md) | bda | $0.059985 | $0.049273 | $0.019985 | -0.029287 | 25.62s | 16.04s | -9.58s | 36% | 48% |
| [synthetic-expense-utility-water-sewer-bill-render-spanish.png](synthetic-expense-utility-water-sewer-bill-render-spanish.md) | bda | $0.058139 | $0.049305 | $0.018139 | -0.031166 | 29.78s | 11.44s | -18.34s | 81% | 90% |
| [synthetic-expense-utility-water-sewer-bill-render.pdf](synthetic-expense-utility-water-sewer-bill-render.md) | bda | $0.056516 | $0.048827 | $0.016516 | -0.032311 | 21.69s | 7.94s | -13.75s | 84% | 89% |
| [synthetic-expense-utility-water-sewer-bill-scan.jpg](synthetic-expense-utility-water-sewer-bill-scan.md) | bda | $0.057301 | $0.049311 | $0.017301 | -0.032010 | 25.14s | 4.08s | -21.06s | 90% | 71% |
| [synthetic-insurance-health-insurance-premium-render-spanish.png](synthetic-insurance-health-insurance-premium-render-spanish.md) | bda | $0.054147 | $0.049298 | $0.014147 | -0.035151 | 25.47s | 2.34s | -23.13s | 91% | 73% |
| [synthetic-insurance-health-insurance-premium-render.pdf](synthetic-insurance-health-insurance-premium-render.md) | bda | $0.053390 | $0.048814 | $0.013390 | -0.035425 | 23.43s | 2.92s | -20.51s | 100% | 82% |
| [synthetic-insurance-health-insurance-premium-scan.jpg](synthetic-insurance-health-insurance-premium-scan.md) | bda | $0.054082 | $0.049276 | $0.014082 | -0.035194 | 21.63s | 2.38s | -19.24s | 91% | 91% |
| [synthetic-investment-and-royalty-income-render-spanish.png](synthetic-investment-and-royalty-income-render-spanish.md) | bda | $0.053039 | $0.049301 | $0.013039 | -0.036262 | 22.74s | 2.19s | -20.55s | 42% | 58% |
| [synthetic-investment-and-royalty-income-render.pdf](synthetic-investment-and-royalty-income-render.md) | bda | $0.051559 | $0.048824 | $0.011559 | -0.037265 | 25.46s | 1.37s | -24.09s | 33% | 100% |
| [synthetic-investment-and-royalty-income-scan.jpg](synthetic-investment-and-royalty-income-scan.md) | bda | $0.053041 | $0.049298 | $0.013041 | -0.036257 | 22.45s | 2.46s | -19.99s | 33% | 67% |
| [synthetic-public-benefits-identity-proof-state-photo-id.jpg](synthetic-public-benefits-identity-proof-state-photo-id.md) | textract | $0.040337 | $0.033874 | $0.015337 | -0.018537 | 2.28s | 3.49s | +1.21s | 92% | 100% |
| [synthetic-public-benefits-income-proof-pay-statement-photo.png](synthetic-public-benefits-income-proof-pay-statement-photo.md) | bda | $0.063583 | $0.048983 | $0.023583 | -0.025400 | 29.14s | 11.99s | -17.15s | 83% | 91% |
| [synthetic-public-benefits-income-proof-pay-statement-rendered.png](synthetic-public-benefits-income-proof-pay-statement-rendered.md) | bda | $0.063482 | $0.048883 | $0.023482 | -0.025401 | 28.83s | 11.52s | -17.31s | 83% | 91% |
| [synthetic-public-benefits-income-proof-pay-stub.jpg](synthetic-public-benefits-income-proof-pay-stub.md) | bda | $0.063452 | $0.048948 | $0.023452 | -0.025496 | 25.70s | 12.32s | -13.38s | 79% | 90% |
| [synthetic-shelter-shelter-verification-render-spanish.png](synthetic-shelter-shelter-verification-render-spanish.md) | bda | $0.052729 | $0.049292 | $0.012729 | -0.036563 | 36.72s | 2.56s | -34.16s | 71% | 43% |
| [synthetic-shelter-shelter-verification-render.pdf](synthetic-shelter-shelter-verification-render.md) | bda | $0.051956 | $0.048808 | $0.011956 | -0.036852 | 32.19s | 1.60s | -30.59s | 100% | 71% |
| [synthetic-shelter-shelter-verification-scan.jpg](synthetic-shelter-shelter-verification-scan.md) | bda | $0.054250 | $0.049276 | $0.014250 | -0.035026 | 21.28s | 3.05s | -18.23s | 80% | 100% |
| [synthetic-snap-income-proof-employment-wage-verification-letter-photo.png](synthetic-snap-income-proof-employment-wage-verification-letter-photo.md) | bda | $0.051813 | $0.049008 | $0.011813 | -0.037195 | 21.47s | 1.28s | -20.19s | 100% | 100% |
| [synthetic-snap-income-proof-employment-wage-verification-letter-rendered.png](synthetic-snap-income-proof-employment-wage-verification-letter-rendered.md) | bda | $0.051684 | $0.048892 | $0.011684 | -0.037208 | 21.60s | 1.44s | -20.16s | 100% | 100% |

