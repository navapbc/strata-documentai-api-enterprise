# synthetic-expense-utility-water-sewer-bill-render.pdf


_Run: 2026-10-01 01:41 UTC_


## Durations

- bda: 27.63s extraction
- ocr-mapping: 3.422s extraction


## Cost

_By Service_
- us.amazon.nova-pro-v1:0: $0.01683200
- bda: $0.04000000
- **total: $0.05683200**

_By Extraction Method_
- shared (preclassification): $0.00882080
- ocr-mapping extraction: $0.00801120
- primary (bda): $0.04000000
- **total: $0.05683200**


## Accuracy

_By Extracted Data_
- BDA: 84% equivalent, 84% close, 16% misses
- OCR Mapping: 89% equivalent, 89% close, 11% misses

_By Bounding Box_
- BDA: 11/15 exact, 4 miss
- OCR Mapping: 10/15 exact, 5 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Bounding Box | BDA Bounding Box | LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| Account_Info.Acct_Name | Jordan Rivera | ✅ Jordan Rivera | ✅ Jordan Rivera | 0.92 | 1.0000 | 0.109,0.319,0.091,0.009|0.109,0.820,0.092,0.009 | ✅ 0.108,0.319,0.092,0.010 | ✅ 0.108,0.319,0.092,0.010 |
| Account_Info.Acct_No | ****-6732 | ✅ ****-6732 | ✅ ****-6732 | 0.44 | 1.0000 | 0.736,0.717,0.072,0.009 | ❌ 0.233,0.156,0.065,0.010 | ❌ 0.232,0.156,0.065,0.010 |
| Account_Info.Meter_Number | 4872915 | ✅ 4872915 | ✅ 4872915 | 0.95 | 1.0000 | 0.233,0.177,0.057,0.009 | ✅ 0.232,0.177,0.058,0.010 | ✅ 0.232,0.177,0.058,0.010 |
| Curr_Meter_Reading | - | - | ❌ 4580 | 0.18 | 1.0000 | - | - | 0.758,0.381,0.090,0.012 |
| Dates.Bill_From_Date | 2026-08-01 | ✅ 08/01/2026 | ✅ 2026-08-01 | 0.85 | 1.0000 | 0.233,0.198,0.078,0.009 | ✅ 0.233,0.198,0.078,0.010 | ✅ 0.233,0.198,0.078,0.010 |
| Dates.Bill_To_Date | 2026-08-31 | ✅ 08/31/2026 | ✅ 2026-08-31 | 0.85 | 1.0000 | 0.333,0.198,0.078,0.010 | ✅ 0.333,0.198,0.078,0.010 | ✅ 0.333,0.198,0.079,0.010 |
| Dates.Billing_Date | 2026-09-05 | ✅ 09/05/2026 | ✅ 2026-09-05 | 0.81 | 1.0000 | 0.233,0.220,0.078,0.009 | ✅ 0.233,0.219,0.078,0.010 | ✅ 0.233,0.219,0.078,0.010 |
| Dates.Due_Date | 2026-09-25 | ✅ 09/25/2026 | ✅ 2026-09-25 | 0.81 | 1.0000 | 0.233,0.241,0.078,0.009|0.736,0.741,0.078,0.009|0.467,0.923,0.078,0.009 | ✅ 0.233,0.240,0.079,0.011 | ✅ 0.233,0.240,0.078,0.011 |
| Line_Items.Amount or Value | 25.48, 18.20, 5.08 | ❌ - | ❌ 4580 gallons, $25.48, $18.20, $5.08 | - | N/A | - | - | 0.758,0.381,0.090,0.012 |
| Line_Items.LineItemDescription | Water Charge, Sewer Charge, Stormwater Fee | ❌ - | ❌ Water Usage, Water Charge, Sewer Charge, Stormwater Fee | - | N/A | - | - | 0.107,0.109,0.180,0.014 |
| Prev_Bal | 62.48 | ✅ 62.48 | ✅ 62.48 | 0.94 | 1.0000 | 0.716,0.178,0.046,0.011 | ✅ 0.715,0.178,0.046,0.012 | ✅ 0.715,0.178,0.046,0.012 |
| Prev_Meter_Reading | - | - | ❌ 4900 | 0.91 | 1.0000 | - | - | 0.773,0.414,0.090,0.012 |
| Provider Name | Harbor County Water Service | ✅ Harbor County Water Service | ✅ Harbor County Water Service | 0.92 | 1.0000 | 0.105,0.024,0.781,0.024|0.109,0.715,0.699,0.015|0.230,0.922,0.534,0.012 | ❌ 0.104,0.024,0.407,0.024 | ❌ 0.104,0.024,0.406,0.024 |
| Service_Address.Building_Line 1 | 1128 Willow Creek Drive | ❌ - | ✅ 1128 Willow Creek Drive | 0.14 | 1.0000 | 0.109,0.836,0.159,0.009 | ❌ - | ❌ 0.109,0.386,0.160,0.010 |
| Service_Address.City | Sedona | ✅ Sedona | ✅ Sedona | 0.92 | N/A | 0.109,0.404,0.053,0.011 | ✅ 0.108,0.404,0.053,0.011 | ❌ - |
| Service_Address.State | AZ | ✅ AZ | ✅ AZ | 0.91 | 1.0000 | 0.167,0.405,0.017,0.009 | ✅ 0.166,0.404,0.019,0.010 | ✅ 0.166,0.404,0.019,0.010 |
| Service_Address.Street | 1128 Willow Creek Drive | ✅ 1128 Willow Creek Drive | ✅ 1128 Willow Creek Drive | 0.94 | 1.0000 | 0.109,0.836,0.159,0.009 | ❌ 0.145,0.386,0.124,0.010 | ❌ 0.109,0.386,0.160,0.010 |
| Service_Address.Zip_Code | 86336 | ✅ 86336 | ✅ 86336 | 0.91 | 1.0000 | 0.190,0.405,0.041,0.009 | ✅ 0.189,0.404,0.041,0.010 | ✅ 0.189,0.404,0.042,0.009 |
| Tot_Amt | 48.76 | ✅ 48.76 | ✅ 48.76 | 0.93 | 1.0000 | 0.716,0.298,0.056,0.014|0.779,0.775,0.060,0.014 | ❌ 0.715,0.264,0.046,0.012 | ❌ 0.715,0.264,0.046,0.012 |
| Total_Current_Charges | 48.76 | ✅ 48.76 | ✅ 48.76 | 0.93 | 1.0000 | 0.716,0.264,0.046,0.011|0.782,0.622,0.046,0.011 | ✅ 0.715,0.264,0.046,0.012 | ✅ 0.715,0.264,0.046,0.012 |
| is_total_amount_greater_than_equal_to_current_charges | True | ✅ True | ✅ True | 0.92 | 1.0000 | - | 0.715,0.178,0.046,0.012 | 0.715,0.264,0.046,0.012 |
