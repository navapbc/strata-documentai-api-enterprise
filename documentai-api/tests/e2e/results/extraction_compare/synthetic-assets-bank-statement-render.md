_Run: 2026-09-25 16:54 UTC_


## synthetic-assets-bank-statement-render.pdf

**Durations**

- bda: 26.86s extraction
- llm: 5.468s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_holder_address | - | 7429 Oak Crest Drive, Little Rock, AR 72205 | 7429 Oak Crest Drive, Little Rock, AR 72205 | 0.89 | 1.0000 | 0.123,0.330,0.383,0.014 | 0.123,0.330,0.383,0.012 | 🟡 |
| account_holder_name | - | Elias K. Thornton | Elias K. Thornton | 0.93 | 1.0000 | 0.124,0.306,0.151,0.013 | 0.124,0.306,0.151,0.013 | ✅ |
| account_number | - | ****5678 | ****5678 | 0.81 | 1.0000 | 0.268,0.207,0.071,0.011 | 0.134,0.207,0.205,0.011 | ❌ |
| account_summary.summary_amount | - | - | 2275.00, 4220.00, 3460.40, 0.00, 3034.60 | - | N/A | - | 0.738,0.591,0.091,0.015 | ❌ |
| account_summary.summary_desc | - | - | Beginning Balance, Total Deposits / Credits, Total Withdrawals / Debits, Fees, Ending Balance | - | N/A | - | 0.135,0.474,0.137,0.015 | ❌ |
| account_type | - | - | - | 0.91 | - | - | - |  |
| bank_name | - | Riverbend Financial Institution | Riverbend Financial Institution | 0.92 | 1.0000 | 0.228,0.045,0.212,0.049 | 0.229,0.079,0.211,0.015 | ❌ |
| branch_transit_number | - | - | - | 0.93 | - | - | - |  |
| statement_end_date | - | 08/31/2026 | 2026-08-31 | 0.75 | 1.0000 | 0.405,0.177,0.089,0.011 | 0.134,0.177,0.360,0.011 | ❌ |
| statement_start_date | - | 06/01/2026 | 2026-06-01 | 0.80 | 1.0000 | 0.291,0.177,0.088,0.011 | 0.134,0.177,0.360,0.011 | ❌ |
