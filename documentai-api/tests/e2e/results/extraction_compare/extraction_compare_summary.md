# Extraction Compare Results

_Run: 2026-10-01 02:38 UTC_

## Avg Durations
- bda: 24.37s
- ocr-mapping: 4.81s
- textract: 2.34s


## Total Cost by Model
- us.amazon.nova-lite-v1:0: $0.003038
- us.amazon.nova-pro-v1:0: $0.571101
- **total: $0.574138**


## Primary Extraction Method vs. LLM via Textract
### Cost & Duration 
| Primary Method | Shared (preclass) | Primary Total | LLM Total | Cost Ratio | Median Primary Duration | Median LLM Duration | Speed Ratio |
|---|---|---|---|---|---|---|---|
| bda | $0.327286 | $1.440000 | $0.231382 | 6.2x cheaper | 23.75s | 2.49s | 9.5x faster |
| textract | $0.008870 | $0.025000 | $0.006600 | 3.8x cheaper | 2.34s | 2.28s | 1.0x faster |


### Accuracy

_Expected field values defined for 520 scored fields (507 bda, 13 textract); bounding-box ground truth resolved for 321 fields._
| Primary Method | Primary Match (Equiv.) | LLM Match (Equiv.) | Primary Match (Equiv+Approx.) | LLM Match (Equiv+Approx.) | Primary Bounding Box Match | LLM Bounding Box Match |
|---|---|---|---|---|---|---|
| bda | 377/507 (74%) | 435/507 (86%) | 389/507 (77%) | 457/507 (90%) | 173/311 (56%) | 173/311 (56%) |
| textract | 12/13 (92%) | 13/13 (100%) | 13/13 (100%) | 13/13 (100%) | 7/10 (70%) | 7/10 (70%) |


## Document Summary

| Document | Method | Total Cost | Primary Cost | LLM Cost | Cost Delta | Primary Duration | LLM Duration | Duration Delta | Primary Match Rate (Equiv+Approx.) | LLM Match Rate (Equiv+Approx.) | Match Rate Delta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| [synthetic-assets-bank-statement-render-spanish.png](synthetic-assets-bank-statement-render-spanish.md) | bda | $0.057724 | $0.049337 | $0.017724 | -0.031613 | 35.58s | 16.74s | -18.84s | 7/15 (47%) | 14/15 (93%) | +46.7% |
| [synthetic-assets-bank-statement-render.pdf](synthetic-assets-bank-statement-render.md) | bda | $0.054146 | $0.048757 | $0.014146 | -0.034611 | 21.62s | 2.47s | -19.15s | 6/8 (75%) | 8/8 (100%) | +25.0% |
| [synthetic-assets-bank-statement-scan.jpg](synthetic-assets-bank-statement-scan.md) | bda | $0.056845 | $0.049282 | $0.016845 | -0.032438 | 25.22s | 11.49s | -13.73s | 8/15 (53%) | 13/15 (87%) | +33.3% |
| [synthetic-assets-life-insurance-policy-render.pdf](synthetic-assets-life-insurance-policy-render.md) | bda | $0.052529 | $0.048830 | $0.012529 | -0.036302 | 23.08s | 1.54s | -21.54s | 10/10 (100%) | 10/10 (100%) | 0% |
| [synthetic-assets-life-insurance-policy-scan.jpg](synthetic-assets-life-insurance-policy-scan.md) | bda | $0.053326 | $0.049279 | $0.013326 | -0.035953 | 22.88s | 7.81s | -15.07s | 10/10 (100%) | 10/10 (100%) | 0% |
| [synthetic-assets-trust-funds-investment-accounts-render-spanish.png](synthetic-assets-trust-funds-investment-accounts-render-spanish.md) | bda | $0.054009 | $0.049276 | $0.014009 | -0.035267 | 22.23s | 1.93s | -20.30s | 9/10 (90%) | 9/10 (90%) | 0% |
| [synthetic-assets-trust-funds-investment-accounts-render.pdf](synthetic-assets-trust-funds-investment-accounts-render.md) | bda | $0.052872 | $0.048789 | $0.012872 | -0.035917 | 23.04s | 11.21s | -11.83s | 7/10 (70%) | 9/10 (90%) | +20.0% |
| [synthetic-assets-trust-funds-investment-accounts-scan.jpg](synthetic-assets-trust-funds-investment-accounts-scan.md) | bda | $0.053855 | $0.049279 | $0.013855 | -0.035424 | 20.94s | 1.98s | -18.96s | 9/10 (90%) | 10/10 (100%) | +10.0% |
| [synthetic-expense-burial-scan-corner-torn.jpg](synthetic-expense-burial-scan-corner-torn.md) | bda | $0.053737 | $0.049311 | $0.013737 | -0.035574 | 26.36s | 1.96s | -24.40s | 7/9 (78%) | 7/9 (78%) | 0% |
| [synthetic-expense-child-support-rendered.pdf](synthetic-expense-child-support-rendered.md) | bda | $0.054718 | $0.048834 | $0.014718 | -0.034116 | 28.58s | 2.26s | -26.32s | 6/6 (100%) | 6/6 (100%) | 0% |
| [synthetic-expense-child-support-scan.jpg](synthetic-expense-child-support-scan.md) | bda | $0.055652 | $0.049266 | $0.015652 | -0.033614 | 27.03s | 3.50s | -23.53s | 14/14 (100%) | 14/14 (100%) | 0% |
| [synthetic-expense-child-support-spanish-picture.png](synthetic-expense-child-support-spanish-picture.md) | bda | $0.055736 | $0.049298 | $0.015736 | -0.033562 | 29.37s | 2.51s | -26.86s | 12/13 (92%) | 11/13 (85%) | -7.7% |
| [synthetic-expense-dependent-care-render.pdf](synthetic-expense-dependent-care-render.md) | bda | $0.052999 | $0.048834 | $0.012999 | -0.035834 | 25.53s | 1.76s | -23.77s | 10/11 (91%) | 11/11 (100%) | +9.1% |
| [synthetic-expense-dependent-care-scan.png](synthetic-expense-dependent-care-scan.md) | bda | $0.054127 | $0.049269 | $0.014127 | -0.035142 | 25.71s | 2.13s | -23.58s | 9/11 (82%) | 11/11 (100%) | +18.2% |
| [synthetic-expense-utility-cable-bill-render-spanish.png](synthetic-expense-utility-cable-bill-render-spanish.md) | bda | $0.056013 | $0.049289 | $0.016013 | -0.033276 | 23.76s | 4.05s | -19.71s | 7/10 (70%) | 10/10 (100%) | +30.0% |
| [synthetic-expense-utility-cable-bill-render.pdf](synthetic-expense-utility-cable-bill-render.md) | bda | $0.054110 | $0.048802 | $0.014110 | -0.034692 | 25.91s | 3.43s | -22.48s | 7/10 (70%) | 10/10 (100%) | +30.0% |
| [synthetic-expense-utility-electric-bill-render-spanish.png](synthetic-expense-utility-electric-bill-render-spanish.md) | bda | $0.059898 | $0.049260 | $0.019898 | -0.029362 | 23.73s | 9.47s | -14.26s | 11/25 (44%) | 17/25 (68%) | +24.0% |
| [synthetic-expense-utility-electric-bill-render.pdf](synthetic-expense-utility-electric-bill-render.md) | bda | $0.058866 | $0.048798 | $0.018866 | -0.029933 | 27.24s | 9.22s | -18.02s | 12/24 (50%) | 20/24 (83%) | +33.3% |
| [synthetic-expense-utility-electric-bill-scan.jpg](synthetic-expense-utility-electric-bill-scan.md) | bda | $0.059770 | $0.049263 | $0.019770 | -0.029493 | 25.10s | 9.46s | -15.64s | 12/25 (48%) | 24/25 (96%) | +48.0% |
| [synthetic-expense-utility-water-sewer-bill-render-spanish.png](synthetic-expense-utility-water-sewer-bill-render-spanish.md) | bda | $0.058292 | $0.049301 | $0.018292 | -0.031010 | 28.97s | 5.06s | -23.91s | 18/21 (86%) | 20/21 (95%) | +9.5% |
| [synthetic-expense-utility-water-sewer-bill-render.pdf](synthetic-expense-utility-water-sewer-bill-render.md) | bda | $0.056880 | $0.048840 | $0.016880 | -0.031960 | 22.24s | 3.14s | -19.10s | 16/19 (84%) | 18/19 (95%) | +10.5% |
| [synthetic-expense-utility-water-sewer-bill-scan.jpg](synthetic-expense-utility-water-sewer-bill-scan.md) | bda | $0.057861 | $0.049340 | $0.017861 | -0.031479 | 23.53s | 3.77s | -19.76s | 19/21 (90%) | 20/21 (95%) | +4.8% |
| [synthetic-insurance-health-insurance-premium-render-spanish.png](synthetic-insurance-health-insurance-premium-render-spanish.md) | bda | $0.054338 | $0.049298 | $0.014338 | -0.034960 | 24.43s | 2.72s | -21.71s | 11/11 (100%) | 9/11 (82%) | -18.2% |
| [synthetic-insurance-health-insurance-premium-render.pdf](synthetic-insurance-health-insurance-premium-render.md) | bda | $0.053453 | $0.048795 | $0.013453 | -0.035342 | 31.87s | 1.77s | -30.10s | 11/11 (100%) | 11/11 (100%) | 0% |
| [synthetic-insurance-health-insurance-premium-scan.jpg](synthetic-insurance-health-insurance-premium-scan.md) | bda | $0.054193 | $0.049276 | $0.014193 | -0.035082 | 20.50s | 2.37s | -18.13s | 11/11 (100%) | 11/11 (100%) | 0% |
| [synthetic-investment-and-royalty-income-render-spanish.png](synthetic-investment-and-royalty-income-render-spanish.md) | bda | $0.053137 | $0.049263 | $0.013137 | -0.036126 | 22.07s | 1.74s | -20.33s | 6/12 (50%) | 7/12 (58%) | +8.3% |
| [synthetic-investment-and-royalty-income-render.pdf](synthetic-investment-and-royalty-income-render.md) | bda | $0.052320 | $0.048789 | $0.012320 | -0.036469 | 21.36s | 2.44s | -18.93s | 2/6 (33%) | 6/6 (100%) | +66.7% |
| [synthetic-investment-and-royalty-income-scan.jpg](synthetic-investment-and-royalty-income-scan.md) | bda | $0.053159 | $0.049282 | $0.013159 | -0.036123 | 22.27s | 1.40s | -20.87s | 5/12 (42%) | 8/12 (67%) | +25.0% |
| [synthetic-public-benefits-identity-proof-state-photo-id.jpg](synthetic-public-benefits-identity-proof-state-photo-id.md) | textract | $0.040470 | $0.033870 | $0.015470 | -0.018400 | 2.34s | 2.28s | -0.06s | 13/13 (100%) | 13/13 (100%) | 0% |
| [synthetic-public-benefits-income-proof-pay-statement-photo.png](synthetic-public-benefits-income-proof-pay-statement-photo.md) | bda | $0.063716 | $0.048980 | $0.023716 | -0.025263 | 23.60s | 12.30s | -11.30s | 29/35 (83%) | 32/35 (91%) | +8.6% |
| [synthetic-public-benefits-income-proof-pay-statement-rendered.png](synthetic-public-benefits-income-proof-pay-statement-rendered.md) | bda | $0.063613 | $0.048864 | $0.023613 | -0.025251 | 24.08s | 12.74s | -11.34s | 29/35 (83%) | 32/35 (91%) | +8.6% |
| [synthetic-public-benefits-income-proof-pay-stub.jpg](synthetic-public-benefits-income-proof-pay-stub.md) | bda | $0.063618 | $0.048977 | $0.023618 | -0.025359 | 23.17s | 11.77s | -11.40s | 23/29 (79%) | 26/29 (90%) | +10.3% |
| [synthetic-shelter-shelter-verification-render-spanish.png](synthetic-shelter-shelter-verification-render-spanish.md) | bda | $0.052904 | $0.049266 | $0.012904 | -0.036362 | 27.21s | 2.25s | -24.96s | 7/7 (100%) | 6/7 (86%) | -14.3% |
| [synthetic-shelter-shelter-verification-render.pdf](synthetic-shelter-shelter-verification-render.md) | bda | $0.052160 | $0.048805 | $0.012160 | -0.036645 | 27.58s | 1.97s | -25.61s | 7/7 (100%) | 6/7 (86%) | -14.3% |
| [synthetic-shelter-shelter-verification-scan.jpg](synthetic-shelter-shelter-verification-scan.md) | bda | $0.054329 | $0.049263 | $0.014329 | -0.034934 | 16.59s | 2.31s | -14.28s | 8/10 (80%) | 9/10 (90%) | +10.0% |
| [synthetic-snap-income-proof-employment-wage-verification-letter-photo.png](synthetic-snap-income-proof-employment-wage-verification-letter-photo.md) | bda | $0.051940 | $0.049012 | $0.011940 | -0.037071 | 17.09s | 1.75s | -15.34s | 7/7 (100%) | 6/7 (86%) | -14.3% |
| [synthetic-snap-income-proof-employment-wage-verification-letter-rendered.png](synthetic-snap-income-proof-employment-wage-verification-letter-rendered.md) | bda | $0.051825 | $0.048883 | $0.011825 | -0.037058 | 17.98s | 1.12s | -16.86s | 7/7 (100%) | 6/7 (86%) | -14.3% |

