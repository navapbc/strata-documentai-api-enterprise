# synthetic-assets-bank-statement-scan.jpg


_Run: 2026-09-28 18:33 UTC_


## Durations

- bda: 21.13s extraction
- llm: 2.717s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384 (1956 in / 27 out)
- us.amazon.nova-pro-v1:0: $0.01488480 (15666 in / 735 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05500864**

_By Extraction Method_
- shared (preclassification): $0.00926944
- llm extraction: $0.00573920
- primary (bda): $0.04000000
- **total: $0.05500864**


## Accuracy
- BDA: 40% exact, 53% loose, 47% misses
- LLM: 27% exact, 27% loose, 73% misses


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_holder_address | 237 WILLOW BEND WAY BALTIMORE, MD 21224 | ✅ 237 WILLOW BEND WAY BALTIMORE, MD 21224 | ✅ 237 WILLOW BEND WAY BALTIMORE, MD 21224 | 0.76 | N/A | 0.108,0.261,0.204,0.029 | 0.108,0.261,0.204,0.010 | ❌ |
| account_holder_name | Alex M. Thompson | ✅ Alex M. Thompson | ✅ Alex M. Thompson | 0.85 | N/A | 0.107,0.244,0.183,0.011 | 0.107,0.244,0.183,0.011 | ✅ |
| account_number | ********5342 | ✅ ********5342 | ❌ *******5342 | 0.58 | 1.0000 | 0.283,0.374,0.094,0.010 | 0.065,0.374,0.062,0.009 | ❌ |
| account_summary.summary_amount | 1225.00, 3110.00, 2550.20, 0.00, 1784.80 | ❌ - | ❌ 1225.00 | - | 1.0000 | - | 0.866,0.202,0.071,0.011 | ❌ |
| account_summary.summary_desc | Beginning Balance, Total Deposits/Credits, Total Withdrawals/Debits, Total Fees, Ending Balance | ❌ - | ❌ Beginning Balance | - | 1.0000 | - | 0.577,0.203,0.135,0.012 | ❌ |
| account_type | Checking | ✅ Checking | ✅ Checking | 0.93 | 1.0000 | 0.283,0.358,0.069,0.012 | 0.065,0.358,0.062,0.010 | ❌ |
| bank_name | Harbor Community Bank | ✅ Harbor Community Bank | ✅ Harbor Community Bank | 0.85 | 1.0000 | 0.178,0.046,0.280,0.053 | 0.179,0.072,0.279,0.027 | ❌ |
| branch_transit_number | ******1250 | ✅ ******1250 | ❌ - | 0.76 | N/A | 0.283,0.391,0.078,0.010 | - | ❌ |
| statement_end_date | 2026-08-31 | 🟡 08/31/2026 | ❌ August 31, 2026 | 0.73 | 1.0000 | 0.747,0.092,0.120,0.012 | 0.609,0.092,0.258,0.012 | ❌ |
| statement_start_date | 2026-08-01 | 🟡 08/01/2026 | ❌ August 01, 2026 | 0.71 | 1.0000 | 0.609,0.092,0.120,0.012 | 0.609,0.092,0.258,0.012 | ❌ |
| transaction_details.balance | 2600.00, 3975.00, 4335.60, 2932.39, 2167.33, 1784.80 | ❌ - | ❌ 2600.00 | - | 1.0000 | - | 0.865,0.516,0.071,0.011 | ❌ |
| transaction_details.date | 08/06/2026, 08/20/2026, 08/27/2026, 08/10/2026, 08/18/2026, 08/25/2026 | ❌ - | ❌ 08/06/2026 | - | 1.0000 | - | 0.071,0.516,0.081,0.009 | ❌ |
| transaction_details.deposits | 1375.00, 1375.00, 360.00, 0.00, 0.00, 0.00 | ❌ - | ❌ 1375.00 | - | 1.0000 | - | 0.560,0.516,0.071,0.011 | ❌ |
| transaction_details.description | DIRECT DEPOSIT Bluewater Solutions LLC PAYROLL, DIRECT DEPOSIT Bluewater Solutions LLC PAYROLL, DIRECT DEPOSIT Bluewater Solutions LLC BONUS, DEBIT CARD PURCHASE Giant Food #6207 Baltimore MD, RENT PAYMENT Greenfield Apartments, ONLINE TRANSFER Alex M. Thompson Savings | ❌ - | ❌ DIRECT DEPOSIT | - | 1.0000 | - | 0.179,0.510,0.118,0.009 | ❌ |
| transaction_details.withdrawals | 0.00, 0.00, 0.00, 1402.61, 765.06, 382.53 | ❌ - | ❌ - | - | 0.9000 | - | 0.786,0.520,0.010,0.002 | ❌ |
