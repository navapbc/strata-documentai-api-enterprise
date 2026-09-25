_Run: 2026-09-25 19:28 UTC_


## synthetic-expense-utility-electric-bill-render.pdf

**Durations**

- bda: 26.24s extraction
- llm: 15.305s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| Account Number | - | - | ****-6729 | - | 0.9900 | - | 0.782,0.085,0.065,0.010 | ❌ |
| Address.Service Address | - | 8734 Meadowbrook Lane, Cheyenne, WY 82001 | 8734 Meadowbrook Lane, Cheyenne, WY 82001 | 0.77 | N/A | 0.114,0.300,0.176,0.029 | 0.114,0.300,0.134,0.010 | ❌ |
| Address.Service address pin code | - | WY 82001 | 82001 | 0.80 | 1.0000 | 0.192,0.317,0.070,0.010 | 0.221,0.317,0.040,0.010 | ❌ |
| BalanceDue Date | - | 09/25/26 | September 25, 2026 | 0.88 | 1.0000 | 0.744,0.172,0.141,0.012 | 0.744,0.172,0.142,0.012 | 🟡 |
| BalanceGreaterCheck | - | - | - | 0.94 | - | 0.677,0.239,0.059,0.012 | - | ❌ |
| Category | - | Electricity | Electricity | 0.66 | 0.9500 | 0.567,0.027,0.156,0.025 | 0.567,0.027,0.156,0.025 | ✅ |
| CountMeterIDs | - | 1 | - | 0.77 | - | 0.156,0.466,0.074,0.010 | - | ❌ |
| Current Balance | - | 94.3 | 94.30 | 0.95 | 1.0000 | 0.677,0.292,0.051,0.012 | 0.677,0.292,0.051,0.012 | ✅ |
| End Date | - | 08/31/26 | August 31, 2026 | 0.89 | 1.0000 | 0.758,0.148,0.112,0.012 | 0.758,0.148,0.112,0.012 | ✅ |
| Is_NumMeterIDsListed | - | - | - | 0.95 | - | 0.156,0.466,0.074,0.010 | - | ❌ |
| Is_PrevGreaterThanCurr | - | - | - | 0.94 | - | - | - |  |
| Is_ValidPinCode | - | True | - | 0.93 | - | 0.222,0.317,0.040,0.010 | - | ❌ |
| Is_ValidState | - | True | - | 0.93 | - | 0.114,0.317,0.103,0.012 | - | ❌ |
| Line_Item_Charges.Charge | - | - | 78.20, 45.00, 33.20, 5.00, 3.10 | - | N/A | - | 0.788,0.810,0.041,0.012 | ❌ |
| Line_Item_Charges.Line item Description | - | - | Energy Consumption (920 kWh at $0.085/kWh), Delivery/Distribution Charge, Supply/Generation Charge, Wyoming Energy Surcharge, Taxes & Fees | - | N/A | - | 0.115,0.715,0.242,0.013 | ❌ |
| Meter Number | - | - | Meter #02348719 | - | 1.0000 | - | 0.114,0.466,0.115,0.009 | ❌ |
| MeterRead.Current value | - | - | 920kWh | - | 1.0000 | - | 0.471,0.485,0.059,0.009 | ❌ |
| MeterRead.Delta or Metered value | - | - | -20kWh | - | N/A | - | 0.380,0.446,0.032,0.010 | ❌ |
| MeterRead.Meter ID | - | - | 02348719 | - | N/A | - | - |  |
| MeterRead.Previous value | - | - | 940kWh | - | 1.0000 | - | 0.779,0.480,0.059,0.009 | ❌ |
| MeterRead.Usage Unit | - | - | kWh | - | 1.0000 | - | 0.380,0.446,0.032,0.010 | ❌ |
| Previous Balance | - | 112.45 | 112.45 | 0.91 | 1.0000 | 0.677,0.239,0.059,0.012 | 0.677,0.239,0.059,0.012 | ✅ |
| Provider | - | Cedar Grove Energy | Cedar Grove Energy | 0.95 | 0.9500 | 0.217,0.027,0.198,0.021 | 0.217,0.027,0.198,0.021 | ✅ |
| StartDate | - | 08/01/26 | August 1, 2026 | 0.91 | 0.9700 | 0.758,0.132,0.104,0.012 | 0.758,0.132,0.105,0.012 | 🟡 |
| Total Balance Due | - | 94.3 | 94.30 | 0.93 | 1.0000 | 0.677,0.323,0.057,0.013 | 0.677,0.292,0.051,0.012 | ❌ |
| Usage.power factor | - | - | 1 | - | 0.9100 | - | 0.438,0.625,0.123,0.010 | ❌ |
| Usage.usage | - | - | 920 kWh | - | 1.0000 | - | 0.471,0.485,0.059,0.009 | ❌ |
| UsageMult | - | - | - | 0.93 | - | - | - |  |
