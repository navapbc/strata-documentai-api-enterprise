# Extraction Compare Results

_Run: 2026-10-28 18:38 UTC_

## Avg Durations
- bda: 26.84s
- ocr-mapping: 4.86s
- textract: 1.38s


## Cost by Model and Service
_Excludes the primary-path fee (BDA or Textract AnalyzeID); see the tables below._
- textract - AnalyzeDocument (layout): $0.140000
- us.amazon.nova-lite-v1:0: $0.002790
- us.amazon.nova-pro-v1:0: $0.542829
- **subtotal: $0.685618**


## Primary Extraction Method vs. LLM via Textract
### Cost & Duration 
| Primary Method | Shared (preclass) | Primary Total | LLM Total | Cost Ratio | Median Primary Duration | Median LLM Duration | Speed Ratio |
|---|---|---|---|---|---|---|---|
| bda | $0.308852 | $1.360000 | $0.357309 | 3.8x cheaper | 25.07s | 3.09s | 8.1x faster |
| textract | $0.008858 | $0.025000 | $0.010600 | 2.4x cheaper | 1.38s | 3.82s | 0.4x slower |


### Accuracy

_Expected field values defined for 498 scored fields (485 bda, 13 textract); bounding-box ground truth resolved for 312 fields._
| Primary Method | Primary Match (Equiv.) | LLM Match (Equiv.) | Primary Match (Equiv+Approx.) | LLM Match (Equiv+Approx.) | Primary Bounding Box Match | LLM Bounding Box Match |
|---|---|---|---|---|---|---|
| bda | 363/485 (75%) | 412/485 (85%) | 370/485 (76%) | 433/485 (89%) | 169/302 (56%) | 172/302 (57%) |
| textract | 12/13 (92%) | 13/13 (100%) | 13/13 (100%) | 13/13 (100%) | 7/10 (70%) | 7/10 (70%) |


## Document Summary

| Document | Method | Total Cost | Primary Cost | LLM Cost | Cost Delta | Primary Duration | LLM Duration | Duration Delta | Primary Match Rate (Equiv+Approx.) | LLM Match Rate (Equiv+Approx.) | Match Rate Delta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| [synthetic-assets-bank-statement-render-spanish.png](synthetic-assets-bank-statement-render-spanish.md) | bda | $0.061509 | $0.049340 | $0.021509 | -0.027830 | 25.03s | 9.36s | -15.67s | 7/15 (47%) | 14/15 (93%) | +46.7% |
| [synthetic-assets-bank-statement-render.pdf](synthetic-assets-bank-statement-render.md) | bda | $0.057784 | $0.048770 | $0.017784 | -0.030986 | 23.10s | 2.68s | -20.42s | 6/8 (75%) | 8/8 (100%) | +25.0% |
| [synthetic-assets-bank-statement-scan.jpg](synthetic-assets-bank-statement-scan.md) | bda | $0.060755 | $0.049253 | $0.020755 | -0.028498 | 22.48s | 6.86s | -15.62s | 8/15 (53%) | 12/15 (80%) | +26.7% |
| [synthetic-assets-life-insurance-policy-render.pdf](synthetic-assets-life-insurance-policy-render.md) | bda | $0.056519 | $0.048821 | $0.016519 | -0.032302 | 29.51s | 2.07s | -27.44s | 10/10 (100%) | 10/10 (100%) | 0% |
| [synthetic-assets-life-insurance-policy-scan.jpg](synthetic-assets-life-insurance-policy-scan.md) | bda | $0.057349 | $0.049301 | $0.017349 | -0.031953 | 25.00s | 2.48s | -22.52s | 10/10 (100%) | 10/10 (100%) | 0% |
| [synthetic-assets-trust-funds-investment-accounts-render-spanish.png](synthetic-assets-trust-funds-investment-accounts-render-spanish.md) | bda | $0.058018 | $0.049285 | $0.018018 | -0.031267 | 22.41s | 2.69s | -19.72s | 9/10 (90%) | 9/10 (90%) | 0% |
| [synthetic-assets-trust-funds-investment-accounts-render.pdf](synthetic-assets-trust-funds-investment-accounts-render.md) | bda | $0.056885 | $0.048802 | $0.016885 | -0.031917 | 27.78s | 2.80s | -24.98s | 7/10 (70%) | 9/10 (90%) | +20.0% |
| [synthetic-assets-trust-funds-investment-accounts-scan.jpg](synthetic-assets-trust-funds-investment-accounts-scan.md) | bda | $0.057893 | $0.049311 | $0.017893 | -0.031418 | 36.05s | 2.17s | -33.88s | 9/10 (90%) | 10/10 (100%) | +10.0% |
| [synthetic-expense-child-support-rendered.pdf](synthetic-expense-child-support-rendered.md) | bda | $0.057671 | $0.048779 | $0.017671 | -0.031108 | 26.96s | 2.63s | -24.33s | 6/6 (100%) | 5/6 (83%) | -16.7% |
| [synthetic-expense-child-support-scan.jpg](synthetic-expense-child-support-scan.md) | bda | $0.059604 | $0.049314 | $0.019604 | -0.029710 | 27.77s | 3.33s | -24.44s | 14/14 (100%) | 14/14 (100%) | 0% |
| [synthetic-expense-dependent-care-render.pdf](synthetic-expense-dependent-care-render.md) | bda | $0.056964 | $0.048776 | $0.016964 | -0.031812 | 22.99s | 1.99s | -21.00s | 10/11 (91%) | 11/11 (100%) | +9.1% |
| [synthetic-expense-dependent-care-scan.png](synthetic-expense-dependent-care-scan.md) | bda | $0.058005 | $0.049301 | $0.018005 | -0.031296 | 25.02s | 2.56s | -22.45s | 9/11 (82%) | 10/11 (91%) | +9.1% |
| [synthetic-expense-utility-cable-bill-render-spanish.png](synthetic-expense-utility-cable-bill-render-spanish.md) | bda | $0.060147 | $0.049285 | $0.020147 | -0.029138 | 25.50s | 4.79s | -20.71s | 7/10 (70%) | 10/10 (100%) | +30.0% |
| [synthetic-expense-utility-cable-bill-render.pdf](synthetic-expense-utility-cable-bill-render.md) | bda | $0.058090 | $0.048782 | $0.018090 | -0.030692 | 28.14s | 4.01s | -24.13s | 7/10 (70%) | 10/10 (100%) | +30.0% |
| [synthetic-expense-utility-electric-bill-render-spanish.png](synthetic-expense-utility-electric-bill-render-spanish.md) | bda | $0.064058 | $0.049276 | $0.024058 | -0.025218 | 24.35s | 9.65s | -14.70s | 11/25 (44%) | 22/25 (88%) | +44.0% |
| [synthetic-expense-utility-electric-bill-render.pdf](synthetic-expense-utility-electric-bill-render.md) | bda | $0.062725 | $0.048786 | $0.022725 | -0.026061 | 38.61s | 9.04s | -29.57s | 12/24 (50%) | 21/24 (88%) | +37.5% |
| [synthetic-expense-utility-electric-bill-scan.jpg](synthetic-expense-utility-electric-bill-scan.md) | bda | $0.063741 | $0.049260 | $0.023741 | -0.025518 | 24.42s | 9.79s | -14.63s | 12/25 (48%) | 23/25 (92%) | +44.0% |
| [synthetic-expense-utility-water-sewer-bill-render-spanish.png](synthetic-expense-utility-water-sewer-bill-render-spanish.md) | bda | $0.062276 | $0.049285 | $0.022276 | -0.027010 | 29.22s | 7.70s | -21.52s | 17/21 (81%) | 20/21 (95%) | +14.3% |
| [synthetic-expense-utility-water-sewer-bill-render.pdf](synthetic-expense-utility-water-sewer-bill-render.md) | bda | $0.060851 | $0.048808 | $0.020851 | -0.027957 | 23.27s | 6.29s | -16.98s | 16/19 (84%) | 18/19 (95%) | +10.5% |
| [synthetic-expense-utility-water-sewer-bill-scan.jpg](synthetic-expense-utility-water-sewer-bill-scan.md) | bda | $0.061854 | $0.049346 | $0.021854 | -0.027492 | 23.69s | 5.42s | -18.27s | 19/21 (90%) | 20/21 (95%) | +4.8% |
| [synthetic-insurance-health-insurance-premium-render-spanish.png](synthetic-insurance-health-insurance-premium-render-spanish.md) | bda | $0.058325 | $0.049285 | $0.018325 | -0.030960 | 29.32s | 2.43s | -26.89s | 11/11 (100%) | 9/11 (82%) | -18.2% |
| [synthetic-insurance-health-insurance-premium-render.pdf](synthetic-insurance-health-insurance-premium-render.md) | bda | $0.057549 | $0.048818 | $0.017549 | -0.031269 | 26.83s | 3.81s | -23.02s | 11/11 (100%) | 11/11 (100%) | 0% |
| [synthetic-insurance-health-insurance-premium-scan.jpg](synthetic-insurance-health-insurance-premium-scan.md) | bda | $0.058229 | $0.049311 | $0.018229 | -0.031082 | 21.79s | 1.97s | -19.82s | 11/11 (100%) | 11/11 (100%) | 0% |
| [synthetic-investment-and-royalty-income-render-spanish.png](synthetic-investment-and-royalty-income-render-spanish.md) | bda | $0.057176 | $0.049301 | $0.017176 | -0.032126 | 28.59s | 2.47s | -26.12s | 8/12 (67%) | 7/12 (58%) | -8.3% |
| [synthetic-investment-and-royalty-income-render.pdf](synthetic-investment-and-royalty-income-render.md) | bda | $0.056314 | $0.048827 | $0.016314 | -0.032514 | 30.57s | 3.09s | -27.48s | 6/6 (100%) | 6/6 (100%) | 0% |
| [synthetic-investment-and-royalty-income-scan.jpg](synthetic-investment-and-royalty-income-scan.md) | bda | $0.057185 | $0.049308 | $0.017185 | -0.032123 | 25.93s | 3.09s | -22.84s | 8/12 (67%) | 8/12 (67%) | 0% |
| [synthetic-public-benefits-identity-proof-state-photo-id.jpg](synthetic-public-benefits-identity-proof-state-photo-id.md) | textract | $0.044458 | $0.033858 | $0.019458 | -0.014400 | 1.38s | 3.82s | +2.44s | 13/13 (100%) | 13/13 (100%) | 0% |
| [synthetic-public-benefits-income-proof-pay-statement-photo.png](synthetic-public-benefits-income-proof-pay-statement-photo.md) | bda | $0.067742 | $0.048992 | $0.027742 | -0.021250 | 25.11s | 15.41s | -9.70s | 29/35 (83%) | 32/35 (91%) | +8.6% |
| [synthetic-public-benefits-income-proof-pay-statement-rendered.png](synthetic-public-benefits-income-proof-pay-statement-rendered.md) | bda | $0.067625 | $0.048880 | $0.027625 | -0.021254 | 43.65s | 11.86s | -31.79s | 29/35 (83%) | 31/35 (89%) | +5.7% |
| [synthetic-public-benefits-income-proof-pay-stub.jpg](synthetic-public-benefits-income-proof-pay-stub.md) | bda | $0.067605 | $0.048968 | $0.027605 | -0.021362 | 24.34s | 11.84s | -12.50s | 23/29 (79%) | 25/29 (86%) | +6.9% |
| [synthetic-shelter-shelter-verification-render-spanish.png](synthetic-shelter-shelter-verification-render-spanish.md) | bda | $0.059189 | $0.049308 | $0.019189 | -0.030119 | 24.14s | 2.88s | -21.27s | 7/7 (100%) | 0/7 (0%) | -100.0% |
| [synthetic-shelter-shelter-verification-render.pdf](synthetic-shelter-shelter-verification-render.md) | bda | $0.056336 | $0.048776 | $0.016336 | -0.032440 | 32.34s | 2.71s | -29.63s | 7/7 (100%) | 7/7 (100%) | 0% |
| [synthetic-shelter-shelter-verification-scan.jpg](synthetic-shelter-shelter-verification-scan.md) | bda | $0.058380 | $0.049272 | $0.018380 | -0.030892 | 23.36s | 3.60s | -19.76s | 0/10 (0%) | 8/10 (80%) | +80.0% |
| [synthetic-snap-income-proof-employment-wage-verification-letter-photo.png](synthetic-snap-income-proof-employment-wage-verification-letter-photo.md) | bda | $0.055950 | $0.049008 | $0.015950 | -0.033058 | 21.40s | 1.28s | -20.12s | 7/7 (100%) | 6/7 (86%) | -14.3% |
| [synthetic-snap-income-proof-employment-wage-verification-letter-rendered.png](synthetic-snap-income-proof-employment-wage-verification-letter-rendered.md) | bda | $0.055856 | $0.048915 | $0.015856 | -0.033058 | 23.95s | 1.47s | -22.48s | 7/7 (100%) | 6/7 (86%) | -14.3% |

