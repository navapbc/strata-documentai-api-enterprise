# synthetic-expense-utility-cable-bill-render.pdf


_Run: 2026-09-29 00:54 UTC_


## Durations

- bda: 25.64s extraction
- llm: 2.762s extraction


## Cost

_By Service_
- us.amazon.nova-pro-v1:0: $0.01411600 (14217 in / 857 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05411600**

_By Extraction Method_
- shared (preclassification): $0.00880800
- llm extraction: $0.00530800
- primary (bda): $0.04000000
- **total: $0.05411600**


## Accuracy
- BDA: 60% equivalent, 60% close, 40% misses
- LLM: 90% equivalent, 90% close, 10% misses


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| Account_Number | 8372-XX-3498 | ❌ ACCT# 8372-XX-3498 | ✅ 8372-XX-3498 | 0.69 | 1.0000 | 0.797,0.073,0.100,0.008 | 0.797,0.073,0.099,0.008 | 🟡 |
| Balance_DueDate | 2026-09-15 | ✅ 09/15/26 | ✅ 2026-09-15 | 0.82 | 1.0000 | 0.827,0.050,0.069,0.008 | 0.270,0.929,0.088,0.011 | ❌ |
| BillingDateBeforeDueDate | True | ✅ True | ✅ True | 0.39 | N/A | 0.827,0.026,0.069,0.009 | 0.827,0.026,0.069,0.009 | ✅ |
| Billing_Date | 2026-08-28 | ✅ 08/28/26 | ✅ 2026-08-28 | 0.80 | 1.0000 | 0.827,0.026,0.069,0.009 | 0.827,0.026,0.069,0.009 | ✅ |
| End_Date | 2026-08-31 | ✅ 08/31/26 | ✅ 2026-08-31 | 0.82 | 0.9900 | 0.764,0.203,0.122,0.013 | 0.627,0.203,0.258,0.013 | ❌ |
| Line_Item_table.Amount | 54.99, 48.00, 8.00, 7.50, 4.76 | ❌ - | ❌ $54.99, $48.00, $8.00, $7.50, $4.76, $112.25 | - | N/A | - | 0.828,0.292,0.057,0.012 | ❌ |
| Line_Item_table.Line item | - | - | ❌ Cable TV Service - Preferred Package, High-Speed Internet Service, Equipment Rental - Set-Top Box, Equipment Rental Modem/Router, Nebraska State Tax and Regulatory Fees, TOTAL NEW CHARGES | - | N/A | - | 0.109,0.601,0.222,0.011 | ❌ |
| Service_Address | 5127 Maplewood Drive, Lincoln, NE 68506 | ✅ 5127 Maplewood Drive, Lincoln, NE 68506 | ✅ 5127 Maplewood Drive, Lincoln, NE 68506 | 0.84 | 1.0000 | 0.110,0.269,0.277,0.012 | 0.110,0.269,0.276,0.012 | 🟡 |
| Start_Date | 2026-08-01 | ✅ 08/01/26 | ✅ 2026-08-01 | 0.83 | 0.9900 | 0.627,0.203,0.124,0.013 | 0.627,0.203,0.258,0.013 | ❌ |
| Summary_table.Amount | 87.50, -87.50, 112.25, 112.25 | ❌ - | ✅ $87.50, -$87.50, $112.25, $112.25 | - | N/A | - | 0.836,0.235,0.049,0.012 | ❌ |
| Summary_table.Description | Previous Balance, Payments Received, New Charges Total, Amount Due | ❌ - | ✅ Previous Balance, Payments Received, New Charges Total, AMOUNT DUE | - | N/A | - | 0.471,0.293,0.090,0.012 | ❌ |
