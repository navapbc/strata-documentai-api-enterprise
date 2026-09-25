_Run: 2026-09-25 19:29 UTC_


## synthetic-expense-utility-water-sewer-bill-render.pdf

**Durations**

- bda: 21.18s extraction
- llm: 4.085s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| Account_Info.Acct_Name | - | Jordan Rivera | Jordan Rivera | 0.92 | 1.0000 | 0.108,0.319,0.092,0.010 | 0.108,0.319,0.092,0.010 | ✅ |
| Account_Info.Acct_No | - | ****-6732 | ****-6732 | 0.44 | 1.0000 | 0.233,0.156,0.065,0.010 | 0.232,0.156,0.065,0.010 | 🟡 |
| Account_Info.Meter_Number | - | 4872915 | 4872915 | 0.95 | 1.0000 | 0.232,0.177,0.058,0.010 | 0.232,0.177,0.058,0.010 | ✅ |
| Curr_Meter_Reading | - | - | 4,580 gallons | 0.18 | 1.0000 | - | 0.758,0.381,0.090,0.012 | ❌ |
| Dates.Bill_From_Date | - | 08/01/2026 | 08/01/2026 | 0.85 | 1.0000 | 0.233,0.198,0.078,0.010 | 0.233,0.198,0.078,0.010 | ✅ |
| Dates.Bill_To_Date | - | 08/31/2026 | 08/31/2026 | 0.85 | 1.0000 | 0.333,0.198,0.078,0.010 | 0.333,0.198,0.079,0.010 | 🟡 |
| Dates.Billing_Date | - | 09/05/2026 | 09/05/2026 | 0.81 | 1.0000 | 0.233,0.219,0.078,0.010 | 0.233,0.219,0.078,0.010 | ✅ |
| Dates.Due_Date | - | 09/25/2026 | 09/25/2026 | 0.81 | 1.0000 | 0.233,0.240,0.079,0.011 | 0.233,0.240,0.078,0.011 | 🟡 |
| Line_Items.Amount or Value | - | - | $25.48 | - | 1.0000 | - | 0.782,0.548,0.045,0.011 | ❌ |
| Line_Items.LineItemDescription | - | - | Water Usage | - | 1.0000 | - | 0.386,0.528,0.085,0.012 | ❌ |
| Prev_Bal | - | 62.48 | 62.48 | 0.94 | 1.0000 | 0.715,0.178,0.046,0.012 | 0.715,0.178,0.046,0.012 | ✅ |
| Prev_Meter_Reading | - | - | 4,900 gallons | 0.91 | 1.0000 | - | 0.773,0.414,0.090,0.012 | ❌ |
| Provider Name | - | Harbor County Water Service | Harbor County Water Service | 0.92 | 1.0000 | 0.104,0.024,0.407,0.024 | 0.104,0.024,0.406,0.024 | 🟡 |
| Service_Address.Building_Line 1 | - | - | 1128 Willow Creek Drive | 0.14 | 1.0000 | - | 0.109,0.386,0.160,0.010 | ❌ |
| Service_Address.City | - | Sedona | Sedona | 0.92 | N/A | 0.108,0.404,0.053,0.011 | - | ❌ |
| Service_Address.State | - | AZ | AZ | 0.91 | 1.0000 | 0.166,0.404,0.019,0.010 | 0.166,0.404,0.019,0.010 | ✅ |
| Service_Address.Street | - | 1128 Willow Creek Drive | 1128 Willow Creek Drive | 0.94 | 1.0000 | 0.145,0.386,0.124,0.010 | 0.109,0.386,0.160,0.010 | ❌ |
| Service_Address.Zip_Code | - | 86336 | 86336 | 0.91 | 1.0000 | 0.189,0.404,0.041,0.010 | 0.189,0.404,0.042,0.009 | 🟡 |
| Tot_Amt | - | 48.76 | 48.76 | 0.93 | 1.0000 | 0.715,0.264,0.046,0.012 | 0.715,0.264,0.046,0.012 | ✅ |
| Total_Current_Charges | - | 48.76 | 48.76 | 0.93 | 1.0000 | 0.715,0.264,0.046,0.012 | 0.715,0.264,0.046,0.012 | ✅ |
| is_total_amount_greater_than_equal_to_current_charges | - | True | Yes | 0.92 | 1.0000 | 0.715,0.178,0.046,0.012 | 0.385,0.645,0.296,0.011 | ❌ |
