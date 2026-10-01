# synthetic-expense-utility-electric-bill-scan.jpg


_Run: 2026-10-01 02:38 UTC_


## Durations

- bda: 25.1s extraction
- ocr-mapping: 9.463s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384
- us.amazon.nova-pro-v1:0: $0.01964640
- bda: $0.04000000
- **total: $0.05977024**

_By Extraction Method_
- shared (preclassification): $0.00926304
- ocr-mapping extraction: $0.01050720
- primary (bda): $0.04000000
- **total: $0.05977024**


## Accuracy

_By Extracted Data_
- BDA: 11/25 (44%) equivalent match, 12/25 (48%) close, 13 misses
- OCR Mapping: 23/25 (92%) equivalent match, 24/25 (96%) close, 1 miss

_By Bounding Box_
- BDA: 6/14 exact, 7 miss
- OCR Mapping: 10/14 exact, 3 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Bounding Box | BDA Bounding Box | LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| Account Number | 1234 5678 9012 | ❌ - | ✅ 1234 5678 9012 | - | 0.9600 | 0.618,0.086,0.270,0.008|0.124,0.805,0.714,0.015 | ❌ - | ❌ 0.782,0.086,0.107,0.009 |
| Address.Service Address | 4912 W Willow Ridge Dr, West Jordan, UT 84081 | ✅ 4912 W Willow Ridge Dr West Jordan, UT 84081 | ✅ 4912 W Willow Ridge Dr, West Jordan, UT 84081 | 0.81 | N/A | 0.658,0.177,0.138,0.023|0.070,0.203,0.169,0.024 | ✅ 0.071,0.202,0.176,0.024 | ✅ 0.659,0.177,0.152,0.010 |
| Address.Service address pin code | 84081 | ❌ UT 84081 | ✅ 84081 | 0.86 | 1.0000 | 0.767,0.191,0.037,0.008|0.196,0.216,0.043,0.009 | ✅ 0.197,0.216,0.044,0.009 | ✅ 0.767,0.191,0.038,0.008 |
| BalanceDue Date | 2026-09-17 | ✅ 09/17/26 | ✅ 2026-09-17 | 0.86 | 0.9900 | - | 0.782,0.119,0.087,0.011 | 0.782,0.119,0.087,0.011 |
| BalanceGreaterCheck | Yes | ❌ - | ❌ False | 0.93 | 1.0000 | - | 0.879,0.263,0.052,0.010 | 0.878,0.263,0.052,0.010 |
| Category | Electricity | 🟡 ELECTRICITY BILL | 🟡 Electric | 0.08 | 1.0000 | 0.659,0.031,0.157,0.014|0.075,0.430,0.094,0.008 | 🟡 0.658,0.031,0.219,0.014 | 🟡 0.658,0.031,0.219,0.014 |
| CountMeterIDs | 1 | ✅ 1 | ✅ 1 | 0.76 | 1.0000 | - | 0.659,0.245,0.103,0.009 | 0.449,0.245,0.038,0.008 |
| Current Balance | 118.63 | ✅ 118.63 | ✅ 118.63 | 0.95 | 1.0000 | 0.870,0.308,0.060,0.010|0.846,0.331,0.084,0.015 | ✅ 0.870,0.308,0.061,0.011 | ✅ 0.870,0.308,0.061,0.011 |
| End Date | 2026-08-26 | ✅ 08/26/26 | ✅ 2026-08-26 | 0.86 | 0.9700 | - | 0.439,0.405,0.047,0.010 | 0.703,0.227,0.131,0.010 |
| Is_NumMeterIDsListed | - | - | ❌ False | 0.86 | 1.0000 | - | 0.659,0.245,0.103,0.009 | 0.449,0.245,0.038,0.008 |
| Is_PrevGreaterThanCurr | No | ❌ - | ✅ False | 0.93 | 0.9900 | - | 0.659,0.405,0.042,0.010 | 0.310,0.643,0.053,0.008 |
| Is_ValidPinCode | True | ✅ True | ✅ True | 0.90 | 1.0000 | - | 0.197,0.216,0.044,0.009 | 0.767,0.191,0.038,0.008 |
| Is_ValidState | True | ✅ True | ✅ True | 0.90 | 1.0000 | - | 0.112,0.216,0.080,0.011 | 0.148,0.124,0.017,0.008 |
| Line_Item_Charges.Charge | 65.52, 47.49, 5.50, 0.96, 4.18, 2.98 | ❌ - | ✅ 65.52, 47.49, 5.50, 0.96, 4.18, 2.98 | - | N/A | - | - | 0.558,0.642,0.042,0.010 |
| Line_Item_Charges.Line item Description | Supply (Generation) Charge, Delivery (Distribution) Charge, Customer Charge, Utah Clean Energy Program, State Sales Tax, Municipal Franchise Fee | ❌ - | ✅ Supply (Generation) Charge, Delivery (Distribution) Charge, Customer Charge, Utah Clean Energy Program, State Sales Tax, Municipal Franchise Fee | - | N/A | - | - | 0.060,0.688,0.165,0.010 |
| Meter Number | CGEM12345678 | ❌ - | ✅ CGEM12345678 | - | 1.0000 | 0.658,0.245,0.103,0.008|0.072,0.405,0.097,0.007 | ❌ - | ✅ 0.658,0.245,0.103,0.009 |
| MeterRead.Current value | 36885 | ❌ - | ✅ 36885 | - | 1.0000 | 0.769,0.402,0.045,0.015 | ❌ - | ✅ 0.768,0.405,0.042,0.009 |
| MeterRead.Delta or Metered value | 640 | ❌ - | ✅ 640 | - | 1.0000 | - | - | 0.913,0.404,0.024,0.008 |
| MeterRead.Meter ID | CGEM12345678 | ❌ - | ✅ CGEM12345678 | - | 1.0000 | 0.658,0.245,0.103,0.008|0.072,0.405,0.097,0.007 | ❌ - | ✅ 0.658,0.245,0.103,0.009 |
| MeterRead.Previous value | 36245 | ❌ - | ✅ 36245 | - | 1.0000 | 0.659,0.405,0.041,0.008 | ❌ - | ✅ 0.659,0.405,0.042,0.009 |
| MeterRead.Usage Unit | kWh | ❌ - | ✅ kWh | - | 0.9200 | 0.902,0.387,0.035,0.009 | ❌ - | ❌ 0.063,0.492,0.011,0.017 |
| Previous Balance | 112.74 | ✅ 112.74 | ✅ 112.74 | 0.88 | 1.0000 | 0.879,0.263,0.051,0.010 | ✅ 0.879,0.263,0.052,0.010 | ✅ 0.878,0.263,0.052,0.010 |
| Provider | Cedar Grove Energy | ✅ Cedar Grove Energy | ✅ Cedar Grove Energy | 0.94 | 1.0000 | 0.165,0.040,0.302,0.022 | ✅ 0.165,0.040,0.303,0.023 | ✅ 0.165,0.040,0.303,0.023 |
| StartDate | 2026-07-28 | ✅ 07/28/26 | ✅ 2026-07-28 | 0.88 | 0.9700 | - | 0.658,0.228,0.077,0.010 | 0.658,0.227,0.176,0.008 |
| Total Balance Due | 118.63 | ✅ 118.63 | ✅ 118.63 | 0.93 | 1.0000 | 0.846,0.331,0.084,0.015 | ✅ 0.846,0.332,0.086,0.015 | ✅ 0.870,0.308,0.061,0.011 |
| Usage.power factor | - | - | ❌ $0.10237 /kWh, $0.07421 /kWh, $0.00150 /kWh | - | N/A | - | - | 0.417,0.642,0.091,0.009 |
| Usage.usage | 640 kWh | ❌ - | ✅ 640 kWh | - | 0.9900 | 0.061,0.642,0.841,0.011|0.061,0.656,0.806,0.011|0.061,0.682,0.752,0.021 | ❌ - | ❌ 0.310,0.643,0.053,0.008 |
| UsageMult | - | - | - | 0.92 | - | - | - | - |
