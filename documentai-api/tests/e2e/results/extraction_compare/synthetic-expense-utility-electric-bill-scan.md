_Run: 2026-09-25 19:28 UTC_


## synthetic-expense-utility-electric-bill-scan.jpg

**Durations**

- bda: 24.47s extraction
- llm: 8.106s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| Account Number | - | - | 1234 5678 9012 | - | 0.9600 | - | 0.782,0.086,0.107,0.009 | ❌ |
| Address.Service Address | - | 4912 W Willow Ridge Dr West Jordan, UT 84081 | 4912 W Willow Ridge Dr
West Jordan, UT 84081 | 0.81 | N/A | 0.071,0.202,0.176,0.024 | 0.659,0.177,0.152,0.010 | ❌ |
| Address.Service address pin code | - | UT 84081 | 84081 | 0.86 | 1.0000 | 0.197,0.216,0.044,0.009 | 0.767,0.191,0.038,0.008 | ❌ |
| BalanceDue Date | - | 09/17/26 | Sep 17, 2026 | 0.86 | 0.9900 | 0.782,0.119,0.087,0.011 | 0.782,0.119,0.087,0.011 | ✅ |
| BalanceGreaterCheck | - | - | - | 0.93 | N/A | 0.879,0.263,0.052,0.010 | - | ❌ |
| Category | - | ELECTRICITY BILL | Electricity | 0.08 | 1.0000 | 0.658,0.031,0.219,0.014 | 0.658,0.031,0.219,0.014 | ✅ |
| CountMeterIDs | - | 1 | 1 | 0.76 | 1.0000 | 0.659,0.245,0.103,0.009 | 0.658,0.245,0.103,0.009 | 🟡 |
| Current Balance | - | 118.63 | 118.63 | 0.95 | 1.0000 | 0.870,0.308,0.061,0.011 | 0.870,0.308,0.061,0.011 | ✅ |
| End Date | - | 08/26/26 | Aug 26, 2026 | 0.86 | 0.9700 | 0.439,0.405,0.047,0.010 | 0.703,0.227,0.131,0.010 | ❌ |
| Is_NumMeterIDsListed | - | - | - | 0.86 | N/A | 0.659,0.245,0.103,0.009 | - | ❌ |
| Is_PrevGreaterThanCurr | - | - | - | 0.93 | N/A | 0.659,0.405,0.042,0.010 | - | ❌ |
| Is_ValidPinCode | - | True | Yes | 0.90 | 1.0000 | 0.197,0.216,0.044,0.009 | 0.767,0.191,0.038,0.008 | ❌ |
| Is_ValidState | - | True | Yes | 0.90 | 1.0000 | 0.112,0.216,0.080,0.011 | 0.148,0.124,0.017,0.008 | ❌ |
| Line_Item_Charges.Charge | - | - | 65.52 | - | 1.0000 | - | 0.558,0.642,0.042,0.010 | ❌ |
| Line_Item_Charges.Line item Description | - | - | Supply (Generation) Charge | - | 1.0000 | - | 0.061,0.643,0.166,0.010 | ❌ |
| Meter Number | - | - | CGEM12345678 | - | 1.0000 | - | 0.658,0.245,0.103,0.009 | ❌ |
| MeterRead.Current value | - | - | 36885 | - | 1.0000 | - | 0.768,0.405,0.042,0.009 | ❌ |
| MeterRead.Delta or Metered value | - | - | 640 | - | 1.0000 | - | 0.913,0.404,0.024,0.008 | ❌ |
| MeterRead.Meter ID | - | - | CGEM12345678 | - | 1.0000 | - | 0.658,0.245,0.103,0.009 | ❌ |
| MeterRead.Previous value | - | - | 36245 | - | 1.0000 | - | 0.659,0.405,0.042,0.009 | ❌ |
| MeterRead.Usage Unit | - | - | kWh | - | 0.9200 | - | 0.063,0.492,0.011,0.017 | ❌ |
| Previous Balance | - | 112.74 | 112.74 | 0.88 | 1.0000 | 0.879,0.263,0.052,0.010 | 0.878,0.263,0.052,0.010 | 🟡 |
| Provider | - | Cedar Grove Energy | Cedar Grove Energy | 0.94 | 1.0000 | 0.165,0.040,0.303,0.023 | 0.165,0.040,0.303,0.023 | ✅ |
| StartDate | - | 07/28/26 | Jul 28, 2026 | 0.88 | 0.9700 | 0.658,0.228,0.077,0.010 | 0.658,0.227,0.176,0.008 | ❌ |
| Total Balance Due | - | 118.63 | 118.63 | 0.93 | 1.0000 | 0.846,0.332,0.086,0.015 | 0.870,0.308,0.061,0.011 | ❌ |
| Usage.power factor | - | - | - | - | N/A | - | - |  |
| Usage.usage | - | - | 640 | - | 1.0000 | - | 0.913,0.404,0.024,0.008 | ❌ |
| UsageMult | - | - | - | 0.92 | N/A | - | - |  |
