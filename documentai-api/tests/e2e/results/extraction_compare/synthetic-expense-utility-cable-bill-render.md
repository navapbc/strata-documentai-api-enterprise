_Run: 2026-09-25 19:28 UTC_


## synthetic-expense-utility-cable-bill-render.pdf

**Durations**

- bda: 23.33s extraction
- llm: 2.225s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| Account_Number | - | ACCT# 8372-XX-3498 | 8372-XX-3498 | 0.69 | 1.0000 | 0.797,0.073,0.100,0.008 | 0.797,0.073,0.099,0.008 | 🟡 |
| Balance_DueDate | - | 09/15/26 | 09/15/2026 | 0.82 | 1.0000 | 0.827,0.050,0.069,0.008 | 0.270,0.929,0.088,0.011 | ❌ |
| BillingDateBeforeDueDate | - | True | Yes | 0.40 | N/A | 0.827,0.026,0.069,0.009 | 0.707,0.026,0.050,0.008 | ❌ |
| Billing_Date | - | 08/28/26 | 08/28/2026 | 0.80 | 1.0000 | 0.827,0.026,0.069,0.009 | 0.827,0.026,0.069,0.009 | ✅ |
| End_Date | - | 08/31/26 | 08/31/2026 | 0.82 | 0.9900 | 0.764,0.203,0.122,0.013 | 0.627,0.203,0.258,0.013 | ❌ |
| Line_Item_table.Amount | - | - | $54.99 | - | 1.0000 | - | 0.413,0.600,0.044,0.011 | ❌ |
| Service_Address | - | 5127 Maplewood Drive, Lincoln, NE 68506 | 5127 Maplewood Drive, Lincoln, NE 68506 | 0.84 | 1.0000 | 0.110,0.269,0.277,0.012 | 0.110,0.269,0.276,0.012 | 🟡 |
| Start_Date | - | 08/01/26 | 08/01/2026 | 0.83 | 0.9900 | 0.627,0.203,0.124,0.013 | 0.627,0.203,0.258,0.013 | ❌ |
| Summary_table.Amount | - | - | $112.25 | - | 1.0000 | - | 0.828,0.292,0.057,0.012 | ❌ |
| Summary_table.Description | - | - | AMOUNT DUE | - | 1.0000 | - | 0.470,0.322,0.070,0.010 | ❌ |
