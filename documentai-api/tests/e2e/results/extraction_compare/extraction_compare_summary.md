# Extraction Compare Results

_Run: 2026-09-29 01:00 UTC_

## Avg Durations
- bda: 25.32s
- llm: 4.56s
- textract: 2.04s


## Total Cost by Model
- us.amazon.nova-lite-v1:0: $0.003037
- us.amazon.nova-pro-v1:0: $0.570444
- **total: $0.573481**


## Primary Extraction Method vs. LLM via Textract
### Cost & Duration 
| Primary Method | Shared (preclass) | Primary Total | LLM Total | LLM vs Primary | Median Primary Duration | Median LLM Duration | LLM vs Primary |
|---|---|---|---|---|---|---|---|
| bda | $0.327327 | $1.440000 | $0.230674 | 6.2x cheaper | 25.03s | 2.33s | 10.7x faster |
| textract | $0.008880 | $0.025000 | $0.006600 | 3.8x cheaper | 2.04s | 2.82s | 0.7x slower |


### Accuracy
| Metric | BDA vs LLM | TEXTRACT vs LLM |
|---|---|---|
| Equivalent Match | 76% / 84% | 92% / 100% |
| Close Match | 78% / 84% | 92% / 100% |


## Document Summary

| Document | Method | Total Cost | Primary Cost | LLM Cost | Cost Delta | Primary Duration | LLM Duration | Duration Delta | Primary Accuracy | LLM Accuracy |
|---|---|---|---|---|---|---|---|---|---|---|
| [synthetic-assets-bank-statement-render-spanish.png](synthetic-assets-bank-statement-render-spanish.md) | bda | $0.059105 | $0.049269 | $0.019105 | -0.030164 | 25.88s | 16.25s | -9.63s | 47% | 73% |
| [synthetic-assets-bank-statement-render.pdf](synthetic-assets-bank-statement-render.md) | bda | $0.053819 | $0.048805 | $0.013819 | -0.034986 | 24.53s | 1.93s | -22.60s | 75% | 100% |
| [synthetic-assets-bank-statement-scan.jpg](synthetic-assets-bank-statement-scan.md) | bda | $0.056813 | $0.049276 | $0.016813 | -0.032463 | 26.02s | 11.22s | -14.80s | 53% | 73% |
| [synthetic-assets-life-insurance-policy-render.pdf](synthetic-assets-life-insurance-policy-render.md) | bda | $0.052497 | $0.048798 | $0.012497 | -0.036302 | 22.56s | 1.50s | -21.06s | 100% | 100% |
| [synthetic-assets-life-insurance-policy-scan.jpg](synthetic-assets-life-insurance-policy-scan.md) | bda | $0.053361 | $0.049314 | $0.013361 | -0.035953 | 23.74s | 7.87s | -15.87s | 100% | 100% |
| [synthetic-assets-trust-funds-investment-accounts-render-spanish.png](synthetic-assets-trust-funds-investment-accounts-render-spanish.md) | bda | $0.054092 | $0.049359 | $0.014092 | -0.035267 | 22.08s | 1.88s | -20.20s | 90% | 90% |
| [synthetic-assets-trust-funds-investment-accounts-render.pdf](synthetic-assets-trust-funds-investment-accounts-render.md) | bda | $0.052853 | $0.048770 | $0.012853 | -0.035917 | 25.62s | 6.87s | -18.75s | 70% | 90% |
| [synthetic-assets-trust-funds-investment-accounts-scan.jpg](synthetic-assets-trust-funds-investment-accounts-scan.md) | bda | $0.053848 | $0.049263 | $0.013848 | -0.035414 | 24.47s | 1.78s | -22.69s | 90% | 100% |
| [synthetic-expense-burial-scan-corner-torn.jpg](synthetic-expense-burial-scan-corner-torn.md) | bda | $0.053708 | $0.049282 | $0.013708 | -0.035574 | 21.29s | 2.72s | -18.57s | 67% | 67% |
| [synthetic-expense-child-support-rendered.pdf](synthetic-expense-child-support-rendered.md) | bda | $0.053818 | $0.048776 | $0.013818 | -0.034958 | 31.24s | 1.83s | -29.40s | 100% | 83% |
| [synthetic-expense-child-support-scan.jpg](synthetic-expense-child-support-scan.md) | bda | $0.055562 | $0.049272 | $0.015562 | -0.033710 | 26.87s | 2.26s | -24.61s | 100% | 93% |
| [synthetic-expense-child-support-spanish-picture.png](synthetic-expense-child-support-spanish-picture.md) | bda | $0.055726 | $0.049282 | $0.015726 | -0.033556 | 29.17s | 2.41s | -26.76s | 77% | 100% |
| [synthetic-expense-dependent-care-render.pdf](synthetic-expense-dependent-care-render.md) | bda | $0.052970 | $0.048782 | $0.012970 | -0.035812 | 22.96s | 1.65s | -21.31s | 91% | 100% |
| [synthetic-expense-dependent-care-scan.png](synthetic-expense-dependent-care-scan.md) | bda | $0.053849 | $0.049266 | $0.013849 | -0.035418 | 25.67s | 1.77s | -23.90s | 82% | 91% |
| [synthetic-expense-utility-cable-bill-render-spanish.png](synthetic-expense-utility-cable-bill-render-spanish.md) | bda | $0.056057 | $0.049276 | $0.016057 | -0.033218 | 25.29s | 4.71s | -20.58s | 70% | 60% |
| [synthetic-expense-utility-cable-bill-render.pdf](synthetic-expense-utility-cable-bill-render.md) | bda | $0.054116 | $0.048808 | $0.014116 | -0.034692 | 25.64s | 2.76s | -22.88s | 60% | 90% |
| [synthetic-expense-utility-electric-bill-render-spanish.png](synthetic-expense-utility-electric-bill-render-spanish.md) | bda | $0.059911 | $0.049273 | $0.019911 | -0.029362 | 26.24s | 9.73s | -16.51s | 44% | 68% |
| [synthetic-expense-utility-electric-bill-render.pdf](synthetic-expense-utility-electric-bill-render.md) | bda | $0.058850 | $0.048782 | $0.018850 | -0.029933 | 25.91s | 10.78s | -15.13s | 50% | 83% |
| [synthetic-expense-utility-electric-bill-scan.jpg](synthetic-expense-utility-electric-bill-scan.md) | bda | $0.059124 | $0.049289 | $0.019124 | -0.030165 | 24.28s | 7.78s | -16.50s | 48% | 72% |
| [synthetic-expense-utility-water-sewer-bill-render-spanish.png](synthetic-expense-utility-water-sewer-bill-render-spanish.md) | bda | $0.058442 | $0.049452 | $0.018442 | -0.031010 | 32.90s | 4.34s | -28.56s | 86% | 95% |
| [synthetic-expense-utility-water-sewer-bill-render.pdf](synthetic-expense-utility-water-sewer-bill-render.md) | bda | $0.056867 | $0.048795 | $0.016867 | -0.031928 | 22.74s | 3.87s | -18.87s | 84% | 89% |
| [synthetic-expense-utility-water-sewer-bill-scan.jpg](synthetic-expense-utility-water-sewer-bill-scan.md) | bda | $0.057813 | $0.049308 | $0.017813 | -0.031495 | 32.64s | 3.54s | -29.09s | 90% | 100% |
| [synthetic-insurance-health-insurance-premium-render-spanish.png](synthetic-insurance-health-insurance-premium-render-spanish.md) | bda | $0.054335 | $0.049295 | $0.014335 | -0.034960 | 29.10s | 2.25s | -26.85s | 100% | 73% |
| [synthetic-insurance-health-insurance-premium-render.pdf](synthetic-insurance-health-insurance-premium-render.md) | bda | $0.053469 | $0.048811 | $0.013469 | -0.035342 | 25.36s | 1.64s | -23.72s | 100% | 91% |
| [synthetic-insurance-health-insurance-premium-scan.jpg](synthetic-insurance-health-insurance-premium-scan.md) | bda | $0.054229 | $0.049311 | $0.014229 | -0.035082 | 22.31s | 1.90s | -20.41s | 100% | 91% |
| [synthetic-investment-and-royalty-income-render-spanish.png](synthetic-investment-and-royalty-income-render-spanish.md) | bda | $0.053153 | $0.049279 | $0.013153 | -0.036126 | 21.16s | 1.82s | -19.34s | 50% | 58% |
| [synthetic-investment-and-royalty-income-render.pdf](synthetic-investment-and-royalty-income-render.md) | bda | $0.052259 | $0.048776 | $0.012259 | -0.036517 | 41.06s | 1.88s | -39.18s | 33% | 100% |
| [synthetic-investment-and-royalty-income-scan.jpg](synthetic-investment-and-royalty-income-scan.md) | bda | $0.053165 | $0.049289 | $0.013165 | -0.036123 | 22.41s | 1.36s | -21.05s | 42% | 67% |
| [synthetic-public-benefits-identity-proof-state-photo-id.jpg](synthetic-public-benefits-identity-proof-state-photo-id.md) | textract | $0.040480 | $0.033880 | $0.015480 | -0.018400 | 2.04s | 2.82s | +0.78s | 92% | 100% |
| [synthetic-public-benefits-income-proof-pay-statement-photo.png](synthetic-public-benefits-income-proof-pay-statement-photo.md) | bda | $0.063761 | $0.049012 | $0.023761 | -0.025250 | 24.77s | 11.98s | -12.79s | 83% | 91% |
| [synthetic-public-benefits-income-proof-pay-statement-rendered.png](synthetic-public-benefits-income-proof-pay-statement-rendered.md) | bda | $0.063628 | $0.048880 | $0.023628 | -0.025251 | 24.27s | 12.49s | -11.78s | 83% | 91% |
| [synthetic-public-benefits-income-proof-pay-stub.jpg](synthetic-public-benefits-income-proof-pay-stub.md) | bda | $0.063605 | $0.048968 | $0.023605 | -0.025362 | 23.30s | 12.65s | -10.65s | 79% | 86% |
| [synthetic-shelter-shelter-verification-render-spanish.png](synthetic-shelter-shelter-verification-render-spanish.md) | bda | $0.052920 | $0.049282 | $0.012920 | -0.036362 | 25.94s | 2.50s | -23.44s | 71% | 43% |
| [synthetic-shelter-shelter-verification-render.pdf](synthetic-shelter-shelter-verification-render.md) | bda | $0.052144 | $0.048789 | $0.012144 | -0.036645 | 30.36s | 1.81s | -28.55s | 100% | 71% |
| [synthetic-shelter-shelter-verification-scan.jpg](synthetic-shelter-shelter-verification-scan.md) | bda | $0.054374 | $0.049266 | $0.014374 | -0.034892 | 17.32s | 1.99s | -15.33s | 80% | 80% |
| [synthetic-snap-income-proof-employment-wage-verification-letter-photo.png](synthetic-snap-income-proof-employment-wage-verification-letter-photo.md) | bda | $0.051931 | $0.048989 | $0.011931 | -0.037058 | 18.36s | 1.33s | -17.03s | 100% | 86% |
| [synthetic-snap-income-proof-employment-wage-verification-letter-rendered.png](synthetic-snap-income-proof-employment-wage-verification-letter-rendered.md) | bda | $0.051824 | $0.048883 | $0.011824 | -0.037058 | 18.23s | 1.04s | -17.19s | 100% | 86% |

