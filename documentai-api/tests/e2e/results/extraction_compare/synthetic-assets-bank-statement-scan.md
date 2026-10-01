# synthetic-assets-bank-statement-scan.jpg


_Run: 2026-10-01 01:41 UTC_


## Durations

- bda: 26.77s extraction
- ocr-mapping: 7.266s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384
- us.amazon.nova-pro-v1:0: $0.01672720
- bda: $0.04000000
- **total: $0.05685104**

_By Extraction Method_
- shared (preclassification): $0.00925984
- ocr-mapping extraction: $0.00759120
- primary (bda): $0.04000000
- **total: $0.05685104**


## Accuracy

_By Extracted Data_
- BDA: 53% equivalent, 53% close, 47% misses
- OCR Mapping: 73% equivalent, 73% close, 27% misses

_By Bounding Box_
- BDA: 2/4 exact, 2 miss
- OCR Mapping: 2/4 exact, 2 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Bounding Box | BDA Bounding Box | LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| account_holder_address | 237 WILLOW BEND WAY BALTIMORE, MD 21224 | ✅ 237 WILLOW BEND WAY BALTIMORE, MD 21224 | ✅ 237 WILLOW BEND WAY, BALTIMORE, MD 21224 | 0.75 | N/A | - | 0.108,0.261,0.204,0.029 | 0.108,0.261,0.204,0.010 |
| account_holder_name | Alex M. Thompson | ✅ Alex M. Thompson | ✅ Alex M. Thompson | 0.86 | N/A | 0.107,0.243,0.182,0.010 | ✅ 0.107,0.244,0.183,0.011 | ✅ 0.107,0.244,0.183,0.011 |
| account_number | ********5342 | ✅ ********5342 | ❌ *******5342 | 0.58 | 1.0000 | - | 0.283,0.374,0.094,0.010 | 0.065,0.374,0.062,0.009 |
| account_summary.summary_amount | 1225.00, 3110.00, 2550.20, 0.00, 1784.80 | ❌ - | ✅ 1225.00, 3110.00, 2550.20, 0.00, 1784.80 | - | N/A | - | - | 0.866,0.202,0.071,0.011 |
| account_summary.summary_desc | Beginning Balance, Total Deposits/Credits, Total Withdrawals/Debits, Total Fees, Ending Balance | ❌ - | ✅ Beginning Balance, Total Deposits/Credits, Total Withdrawals/Debits, Total Fees, Ending Balance | - | N/A | - | - | 0.577,0.203,0.135,0.012 |
| account_type | Checking | ✅ Checking | ✅ Checking | 0.93 | 1.0000 | 0.283,0.357,0.067,0.012 | ✅ 0.283,0.358,0.069,0.012 | ❌ 0.065,0.358,0.062,0.010 |
| bank_name | Harbor Community Bank | ✅ Harbor Community Bank | ✅ Harbor Community Bank | 0.85 | 1.0000 | 0.159,0.924,0.207,0.011 | ❌ 0.178,0.046,0.280,0.053 | ❌ 0.179,0.072,0.279,0.027 |
| branch_transit_number | ******1250 | ✅ ******1250 | ✅ ******1250 | 0.76 | 1.0000 | - | 0.283,0.391,0.078,0.010 | 0.066,0.390,0.057,0.012 |
| statement_end_date | 2026-08-31 | ✅ 08/31/2026 | ✅ 2026-08-31 | 0.73 | 1.0000 | 0.608,0.092,0.257,0.011 | ❌ 0.747,0.092,0.120,0.012 | ✅ 0.609,0.092,0.258,0.012 |
| statement_start_date | 2026-08-01 | ✅ 08/01/2026 | ✅ 2026-08-01 | 0.71 | 1.0000 | - | 0.609,0.092,0.120,0.012 | 0.609,0.092,0.258,0.012 |
| transaction_details.balance | 2600.00, 3975.00, 4335.60, 2932.39, 2167.33, 1784.80 | ❌ - | ✅ 2600.00, 3975.00, 4335.60, 2932.39, 2167.33, 1784.80 | - | N/A | - | - | 0.862,0.292,0.075,0.011 |
| transaction_details.date | 2026-08-06, 2026-08-20, 2026-08-27, 2026-08-10, 2026-08-18, 2026-08-25 | ❌ - | ✅ 2026-08-06, 2026-08-20, 2026-08-27, 2026-08-10, 2026-08-18, 2026-08-25 | - | N/A | - | - | 0.071,0.516,0.081,0.009 |
| transaction_details.deposits | 1375.00, 1375.00, 360.00, 0.00, 0.00, 0.00 | ❌ - | ❌ 1375.00, 1375.00, 360.00, -, -, - | - | N/A | - | - | 0.560,0.516,0.071,0.011 |
| transaction_details.description | DIRECT DEPOSIT Bluewater Solutions LLC PAYROLL, DIRECT DEPOSIT Bluewater Solutions LLC PAYROLL, DIRECT DEPOSIT Bluewater Solutions LLC BONUS, DEBIT CARD PURCHASE Giant Food #6207 Baltimore MD, RENT PAYMENT Greenfield Apartments, ONLINE TRANSFER Alex M. Thompson Savings | ❌ - | ❌ DIRECT DEPOSIT, DIRECT DEPOSIT, DIRECT DEPOSIT, DEBIT CARD PURCHASE, RENT PAYMENT, ONLINE TRANSFER | - | N/A | - | - | 0.178,0.634,0.171,0.009 |
| transaction_details.withdrawals | 0.00, 0.00, 0.00, 1402.61, 765.06, 382.53 | ❌ - | ❌ -, -, -, 1402.61, 765.06, 382.53 | - | N/A | - | - | 0.786,0.520,0.010,0.002 |
