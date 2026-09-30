# synthetic-expense-utility-water-sewer-bill-scan.jpg


_Run: 2026-09-30 16:51 UTC_


## Durations

- bda: 26.17s extraction
- ocr-mapping: 3.885s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384
- us.amazon.nova-pro-v1:0: $0.01797040
- bda: $0.04000000
- **total: $0.05809424**

_By Extraction Method_
- shared (preclassification): $0.00930784
- ocr-mapping extraction: $0.00878640
- primary (bda): $0.04000000
- **total: $0.05809424**


## Accuracy

_By Extracted Data_
- BDA: 90% equivalent, 90% close, 10% misses
- OCR Mapping: 100% equivalent, 100% close, 0% misses

_By Geometry_
- BDA: 5/10 exact, 5 miss
- OCR Mapping: 5/10 exact, 5 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Geo | BDA Geometry | LLM Geometry |
|---|---|---|---|---|---|---|---|---|
| Account_Info.Acct_Name | Jordan Rivera | ✅ Jordan Rivera | ✅ Jordan Rivera | 0.85 | 1.0000 | 0.195,0.875,0.092,0.010 | ❌ 0.699,0.174,0.092,0.010 | ❌ 0.699,0.174,0.092,0.009 |
| Account_Info.Acct_No | XXXX-XXXX-7821 | ✅ XXXX-XXXX-7821 | ✅ XXXX-XXXX-7821 | 0.71 | 1.0000 | 0.698,0.257,0.116,0.009 | ✅ 0.698,0.257,0.118,0.009 | ✅ 0.698,0.257,0.118,0.009 |
| Account_Info.Meter_Number | MTR-1845726 | ✅ MTR-1845726 | ✅ MTR-1845726 | 0.91 | 1.0000 | 0.699,0.275,0.094,0.008 | ✅ 0.699,0.275,0.095,0.010 | ✅ 0.699,0.275,0.096,0.009 |
| Curr_Meter_Reading | 26730 | ✅ 26,730 | ✅ 26,730 | 0.64 | 1.0000 | 0.326,0.408,0.040,0.018 | ✅ 0.326,0.413,0.042,0.010 | ✅ 0.326,0.413,0.041,0.010 |
| Dates.Bill_From_Date | 2026-07-24 | ✅ 07/24/2026 | ✅ 2026-07-24 | 0.67 | 0.9800 | - | 0.191,0.344,0.082,0.010 | 0.191,0.344,0.183,0.009 |
| Dates.Bill_To_Date | 2026-08-24 | ✅ 08/24/2026 | ✅ 2026-08-24 | 0.65 | 0.9800 | - | 0.288,0.345,0.086,0.010 | 0.242,0.344,0.132,0.009 |
| Dates.Billing_Date | 2026-08-25 | ✅ 08/25/2026 | ✅ 2026-08-25 | 0.71 | 1.0000 | - | 0.824,0.074,0.094,0.012 | 0.824,0.074,0.095,0.012 |
| Dates.Due_Date | 2026-09-15 | ✅ 09/15/2026 | ✅ 2026-09-15 | 0.72 | 1.0000 | - | 0.824,0.090,0.095,0.012 | 0.824,0.090,0.095,0.012 |
| Line_Items.Amount or Value | 14.45, 18.99, 20.37, 17.54, 3.50, 0.04 | ❌ - | ✅ 14.45, 18.99, 20.37, 17.54, 3.50, 0.04 | - | N/A | - | - | 0.560,0.539,0.042,0.010 |
| Line_Items.LineItemDescription | Water Service Charge, Water Usage Charge, Sewer Service Charge, Sewer Usage Charge, Stormwater Fee, Colorado Water Conservation Fee | ❌ - | ✅ Water Service Charge, Water Usage Charge, Sewer Service Charge, Sewer Usage Charge, Stormwater Fee, Colorado Water Conservation Fee | - | N/A | - | - | 0.076,0.649,0.207,0.010 |
| Prev_Bal | 48.73 | ✅ 48.73 | ✅ 48.73 | 0.91 | 1.0000 | 0.431,0.173,0.044,0.010 | ✅ 0.431,0.173,0.045,0.011 | ✅ 0.431,0.173,0.045,0.011 |
| Prev_Meter_Reading | 23010 | ✅ 23,010 | ✅ 23,010 | 0.73 | 1.0000 | 0.326,0.431,0.040,0.010 | ✅ 0.326,0.431,0.042,0.010 | ✅ 0.326,0.431,0.041,0.010 |
| Provider Name | Harbor County Water Service | ✅ Harbor County Water Service | ✅ Harbor County Water Service | 0.89 | 1.0000 | - | 0.196,0.036,0.354,0.020 | 0.196,0.036,0.354,0.020 |
| Service_Address.Building_Line 1 | 4824 Aspen Ridge Dr | ✅ 4824 Aspen Ridge Dr | ✅ 4824 Aspen Ridge Dr | 0.80 | 1.0000 | 0.195,0.894,0.139,0.012 | ❌ 0.699,0.192,0.144,0.012 | ❌ 0.699,0.192,0.144,0.012 |
| Service_Address.City | Loveland | ✅ Loveland | ✅ Loveland | 0.84 | N/A | - | 0.699,0.206,0.065,0.011 | - |
| Service_Address.State | CO | ✅ CO | ✅ CO | 0.89 | 0.9900 | - | 0.769,0.207,0.020,0.009 | 0.286,0.099,0.021,0.010 |
| Service_Address.Street | 4824 Aspen Ridge Dr | ✅ 4824 Aspen Ridge Dr | ✅ 4824 Aspen Ridge Dr | 0.88 | 1.0000 | 0.195,0.894,0.139,0.012 | ❌ 0.737,0.192,0.106,0.011 | ❌ 0.699,0.192,0.144,0.012 |
| Service_Address.Zip_Code | 80538 | ✅ 80538 | ✅ 80538 | 0.90 | 0.9800 | - | 0.793,0.207,0.043,0.009 | 0.793,0.207,0.042,0.009 |
| Tot_Amt | 64.86 | ✅ 64.86 | ✅ 64.86 | 0.90 | 1.0000 | 0.843,0.868,0.063,0.014 | ❌ 0.430,0.244,0.046,0.011 | ❌ 0.430,0.244,0.046,0.011 |
| Total_Current_Charges | 64.86 | ✅ 64.86 | ✅ 64.86 | 0.91 | 1.0000 | 0.843,0.868,0.063,0.014 | ❌ 0.430,0.244,0.046,0.011 | ❌ 0.430,0.244,0.046,0.011 |
| is_total_amount_greater_than_equal_to_current_charges | True | ✅ True | ✅ True | 0.89 | N/A | - | 0.430,0.244,0.046,0.011 | 0.082,0.190,0.223,0.011 |
