# DocumentAI - Extraction Comparison

_Last run: 2026-10-30 03:20 UTC - 35 documents_

## Cost by Model and Service

_Excludes the primary-path fee (BDA or Textract AnalyzeID); see the tables below._

- textract - AnalyzeDocument (layout): $0.140000
- us.amazon.nova-lite-v1:0: $0.002790
- us.amazon.nova-pro-v1:0: $0.543152
- **subtotal: $0.685942**

## Extraction Comparison

### BDA vs. Textract OCR / LLM Mapping

<table style="width:100%">
<tr>
<td style="text-align:center;"><img src="charts/extraction_compare_bda_vs_llm_chart.png" alt="BDA vs LLM" style="max-width:400px;"/></td>
</tr>
<tr>
<td><table>
<tr><th>Metric</th><th>BDA</th><th>OCR / LLM</th><th>Delta</th></tr>
<tr><td>Speed (median)</td><td>25.45s</td><td>3.40s</td><td style="color:#16a34a">7.5x faster</td></tr>
<tr><td>Cost</td><td>$1.3600</td><td>$0.3576</td><td style="color:#16a34a">3.8x cheaper</td></tr>
<tr><td>Accuracy (Equiv.)</td><td>357/485 (74%)</td><td>420/485 (87%)</td><td style="color:#16a34a">+13 pts</td></tr>
<tr><td>Accuracy (Equiv+Approx.)</td><td>363/485 (75%)</td><td>436/485 (90%)</td><td style="color:#16a34a">+15 pts</td></tr>
<tr><td>Bounding Box</td><td>167/302 (55%)</td><td>170/302 (56%)</td><td style="color:#16a34a">+1 pts</td></tr>
</table></td>
</tr>
</table>

### Textract Identity vs. Textract OCR / LLM Mapping

<table style="width:100%">
<tr>
<td style="text-align:center;"><img src="charts/extraction_compare_textract_vs_llm_chart.png" alt="Textract vs LLM" style="max-width:400px;"/></td>
</tr>
<tr>
<td><table>
<tr><th>Metric</th><th>Textract</th><th>OCR / LLM</th><th>Delta</th></tr>
<tr><td>Speed (median)</td><td>1.35s</td><td>2.19s</td><td style="color:#dc2626">1.6x slower</td></tr>
<tr><td>Cost</td><td>$0.0250</td><td>$0.0106</td><td style="color:#16a34a">2.4x cheaper</td></tr>
<tr><td>Accuracy (Equiv.)</td><td>12/13 (92%)</td><td>13/13 (100%)</td><td style="color:#16a34a">+8 pts</td></tr>
<tr><td>Accuracy (Equiv+Approx.)</td><td>13/13 (100%)</td><td>13/13 (100%)</td><td style="color:#16a34a">+0 pts</td></tr>
<tr><td>Bounding Box</td><td>7/10 (70%)</td><td>7/10 (70%)</td><td style="color:#16a34a">+0 pts</td></tr>
</table></td>
</tr>
</table>

## Document Summary

| Document | Primary Method | Total Cost | Primary Cost | OCR/LLM Cost | Cost Delta | Primary Duration | OCR/LLM Duration | Duration Delta | Primary Match Rate (Equiv+Approx.) | OCR/LLM Match Rate (Equiv+Approx.) | Match Rate Delta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| [synthetic-assets-bank-statement-render-spanish](md/synthetic-assets-bank-statement-render-spanish.md) | bda | $0.061685 | $0.049298 | $0.021685 | -0.027613 | 24.76s | 8.20s | -16.56s | 7/15 (47%) | 14/15 (93%) | +46.7% |
| [synthetic-assets-bank-statement-render](md/synthetic-assets-bank-statement-render.md) | bda | $0.057803 | $0.048789 | $0.017803 | -0.030986 | 25.46s | 5.92s | -19.54s | 6/8 (75%) | 8/8 (100%) | +25.0% |
| [synthetic-assets-bank-statement-scan](md/synthetic-assets-bank-statement-scan.md) | bda | $0.060844 | $0.049295 | $0.020844 | -0.028450 | 28.42s | 8.93s | -19.49s | 8/15 (53%) | 13/15 (87%) | +33.3% |
| [synthetic-assets-life-insurance-policy-render](md/synthetic-assets-life-insurance-policy-render.md) | bda | $0.056529 | $0.048830 | $0.016529 | -0.032302 | 24.24s | 4.90s | -19.34s | 10/10 (100%) | 10/10 (100%) | 0% |
| [synthetic-assets-life-insurance-policy-scan](md/synthetic-assets-life-insurance-policy-scan.md) | bda | $0.057336 | $0.049289 | $0.017336 | -0.031953 | 22.79s | 5.62s | -17.17s | 10/10 (100%) | 10/10 (100%) | 0% |
| [synthetic-assets-trust-funds-investment-accounts-render-spanish](md/synthetic-assets-trust-funds-investment-accounts-render-spanish.md) | bda | $0.058008 | $0.049276 | $0.018008 | -0.031267 | 25.44s | 6.17s | -19.27s | 9/10 (90%) | 9/10 (90%) | 0% |
| [synthetic-assets-trust-funds-investment-accounts-render](md/synthetic-assets-trust-funds-investment-accounts-render.md) | bda | $0.056891 | $0.048808 | $0.016891 | -0.031917 | 23.76s | 1.93s | -21.83s | 7/10 (70%) | 9/10 (90%) | +20.0% |
| [synthetic-assets-trust-funds-investment-accounts-scan](md/synthetic-assets-trust-funds-investment-accounts-scan.md) | bda | $0.057858 | $0.049273 | $0.017858 | -0.031414 | 21.12s | 2.30s | -18.82s | 9/10 (90%) | 10/10 (100%) | +10.0% |
| [synthetic-expense-child-support-rendered](md/synthetic-expense-child-support-rendered.md) | bda | $0.057610 | $0.048824 | $0.017610 | -0.031214 | 28.23s | 1.60s | -26.63s | 6/6 (100%) | 5/6 (83%) | -16.7% |
| [synthetic-expense-child-support-scan](md/synthetic-expense-child-support-scan.md) | bda | $0.059601 | $0.049324 | $0.019601 | -0.029723 | 29.79s | 3.15s | -26.64s | 14/14 (100%) | 14/14 (100%) | 0% |
| [synthetic-expense-dependent-care-render](md/synthetic-expense-dependent-care-render.md) | bda | $0.056986 | $0.048798 | $0.016986 | -0.031812 | 21.77s | 1.72s | -20.05s | 10/11 (91%) | 11/11 (100%) | +9.1% |
| [synthetic-expense-dependent-care-scan](md/synthetic-expense-dependent-care-scan.md) | bda | $0.058133 | $0.049276 | $0.018133 | -0.031142 | 24.05s | 2.59s | -21.46s | 9/11 (82%) | 11/11 (100%) | +18.2% |
| [synthetic-expense-utility-cable-bill-render-spanish](md/synthetic-expense-utility-cable-bill-render-spanish.md) | bda | $0.059942 | $0.049285 | $0.019942 | -0.029343 | 25.25s | 5.72s | -19.53s | 7/10 (70%) | 10/10 (100%) | +30.0% |
| [synthetic-expense-utility-cable-bill-render](md/synthetic-expense-utility-cable-bill-render.md) | bda | $0.058154 | $0.048846 | $0.018154 | -0.030692 | 24.23s | 3.66s | -20.57s | 7/10 (70%) | 10/10 (100%) | +30.0% |
| [synthetic-expense-utility-electric-bill-render-spanish](md/synthetic-expense-utility-electric-bill-render-spanish.md) | bda | $0.064177 | $0.049295 | $0.024177 | -0.025118 | 24.19s | 9.27s | -14.92s | 11/25 (44%) | 22/25 (88%) | +44.0% |
| [synthetic-expense-utility-electric-bill-render](md/synthetic-expense-utility-electric-bill-render.md) | bda | $0.062872 | $0.048805 | $0.022872 | -0.025933 | 39.83s | 8.98s | -30.84s | 12/24 (50%) | 20/24 (83%) | +33.3% |
| [synthetic-expense-utility-electric-bill-scan](md/synthetic-expense-utility-electric-bill-scan.md) | bda | $0.063668 | $0.049298 | $0.023668 | -0.025630 | 26.38s | 8.50s | -17.88s | 12/25 (48%) | 24/25 (96%) | +48.0% |
| [synthetic-expense-utility-water-sewer-bill-render-spanish](md/synthetic-expense-utility-water-sewer-bill-render-spanish.md) | bda | $0.062298 | $0.049308 | $0.022298 | -0.027010 | 32.27s | 5.79s | -26.48s | 17/21 (81%) | 20/21 (95%) | +14.3% |
| [synthetic-expense-utility-water-sewer-bill-render](md/synthetic-expense-utility-water-sewer-bill-render.md) | bda | $0.060867 | $0.048843 | $0.020867 | -0.027976 | 24.12s | 5.05s | -19.07s | 16/19 (84%) | 18/19 (95%) | +10.5% |
| [synthetic-expense-utility-water-sewer-bill-scan](md/synthetic-expense-utility-water-sewer-bill-scan.md) | bda | $0.061765 | $0.049292 | $0.021765 | -0.027527 | 24.19s | 3.82s | -20.37s | 19/21 (90%) | 20/21 (95%) | +4.8% |
| [synthetic-insurance-health-insurance-premium-render-spanish](md/synthetic-insurance-health-insurance-premium-render-spanish.md) | bda | $0.058313 | $0.049273 | $0.018313 | -0.030960 | 26.12s | 2.32s | -23.80s | 11/11 (100%) | 9/11 (82%) | -18.2% |
| [synthetic-insurance-health-insurance-premium-render](md/synthetic-insurance-health-insurance-premium-render.md) | bda | $0.057514 | $0.048782 | $0.017514 | -0.031269 | 27.32s | 2.23s | -25.09s | 11/11 (100%) | 11/11 (100%) | 0% |
| [synthetic-insurance-health-insurance-premium-scan](md/synthetic-insurance-health-insurance-premium-scan.md) | bda | $0.058273 | $0.049289 | $0.018273 | -0.031015 | 27.00s | 2.42s | -24.57s | 11/11 (100%) | 11/11 (100%) | 0% |
| [synthetic-investment-and-royalty-income-render-spanish](md/synthetic-investment-and-royalty-income-render-spanish.md) | bda | $0.057153 | $0.049279 | $0.017153 | -0.032126 | 27.15s | 1.90s | -25.25s | 8/12 (67%) | 7/12 (58%) | -8.3% |
| [synthetic-investment-and-royalty-income-render](md/synthetic-investment-and-royalty-income-render.md) | bda | $0.056256 | $0.048773 | $0.016256 | -0.032517 | 29.87s | 2.36s | -27.51s | 6/6 (100%) | 6/6 (100%) | 0% |
| [synthetic-investment-and-royalty-income-scan](md/synthetic-investment-and-royalty-income-scan.md) | bda | $0.057162 | $0.049285 | $0.017162 | -0.032123 | 27.27s | 1.76s | -25.51s | 8/12 (67%) | 8/12 (67%) | 0% |
| [synthetic-public-benefits-identity-proof-state-photo-id](md/synthetic-public-benefits-identity-proof-state-photo-id.md) | textract | $0.044454 | $0.033854 | $0.019454 | -0.014400 | 1.35s | 2.19s | +0.84s | 13/13 (100%) | 13/13 (100%) | 0% |
| [synthetic-public-benefits-income-proof-pay-statement-photo](md/synthetic-public-benefits-income-proof-pay-statement-photo.md) | bda | $0.067764 | $0.049015 | $0.027764 | -0.021250 | 24.83s | 11.50s | -13.33s | 29/35 (83%) | 32/35 (91%) | +8.6% |
| [synthetic-public-benefits-income-proof-pay-statement-rendered](md/synthetic-public-benefits-income-proof-pay-statement-rendered.md) | bda | $0.067661 | $0.048912 | $0.027661 | -0.021251 | 24.11s | 11.34s | -12.77s | 29/35 (83%) | 32/35 (91%) | +8.6% |
| [synthetic-public-benefits-income-proof-pay-stub](md/synthetic-public-benefits-income-proof-pay-stub.md) | bda | $0.067605 | $0.048968 | $0.027605 | -0.021362 | 25.80s | 12.06s | -13.74s | 23/29 (79%) | 25/29 (86%) | +6.9% |
| [synthetic-shelter-shelter-verification-render-spanish](md/synthetic-shelter-shelter-verification-render-spanish.md) | bda | $0.059201 | $0.049321 | $0.019201 | -0.030119 | 28.06s | 2.35s | -25.71s | 0/7 (0%) | 0/7 (0%) | 0% |
| [synthetic-shelter-shelter-verification-render](md/synthetic-shelter-shelter-verification-render.md) | bda | $0.056362 | $0.048802 | $0.016362 | -0.032440 | 29.57s | 2.72s | -26.85s | 7/7 (100%) | 7/7 (100%) | 0% |
| [synthetic-shelter-shelter-verification-scan](md/synthetic-shelter-shelter-verification-scan.md) | bda | $0.058416 | $0.049273 | $0.018416 | -0.030857 | 25.64s | 3.06s | -22.58s | 0/10 (0%) | 8/10 (80%) | +80.0% |
| [synthetic-snap-income-proof-employment-wage-verification-letter-photo](md/synthetic-snap-income-proof-employment-wage-verification-letter-photo.md) | bda | $0.055940 | $0.048999 | $0.015940 | -0.033058 | 22.23s | 1.79s | -20.44s | 7/7 (100%) | 6/7 (86%) | -14.3% |
| [synthetic-snap-income-proof-employment-wage-verification-letter-rendered](md/synthetic-snap-income-proof-employment-wage-verification-letter-rendered.md) | bda | $0.055837 | $0.048896 | $0.015837 | -0.033058 | 22.09s | 2.71s | -19.38s | 7/7 (100%) | 6/7 (86%) | -14.3% |
