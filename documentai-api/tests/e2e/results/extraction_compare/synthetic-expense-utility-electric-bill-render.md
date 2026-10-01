# synthetic-expense-utility-electric-bill-render.pdf


_Run: 2026-09-30 19:07 UTC_


## Durations

- bda: 26.16s extraction
- ocr-mapping: 8.997s extraction


## Cost

_By Service_
- us.amazon.nova-pro-v1:0: $0.01865440
- bda: $0.04000000
- **total: $0.05865440**

_By Extraction Method_
- shared (preclassification): $0.00879200
- ocr-mapping extraction: $0.00986240
- primary (bda): $0.04000000
- **total: $0.05865440**


## Accuracy

_By Extracted Data_
- BDA: 50% equivalent, 50% close, 50% misses
- OCR Mapping: 75% equivalent, 75% close, 25% misses

_By Geometry_
- BDA: 4/7 exact, 3 miss
- OCR Mapping: 6/14 exact, 8 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Geo | BDA Geometry | LLM Geometry |
|---|---|---|---|---|---|---|---|---|
| Account Number | ****-6729 | ❌ - | ✅ ****-6729 | - | 0.9900 | 0.783,0.085,0.064,0.009 | ❌ - | ✅ 0.782,0.085,0.065,0.010 |
| Address.Service Address | 8734 Meadowbrook Lane, Cheyenne, WY 82001 | ✅ 8734 Meadowbrook Lane, Cheyenne, WY 82001 | ✅ 8734 Meadowbrook Lane, Cheyenne, WY 82001 | 0.77 | N/A | 0.114,0.300,0.176,0.028 | ✅ 0.114,0.300,0.176,0.029 | ❌ 0.114,0.300,0.134,0.010 |
| Address.Service address pin code | 82001 | ❌ WY 82001 | ✅ 82001 | 0.80 | 1.0000 | 0.221,0.317,0.039,0.009 | ❌ 0.192,0.317,0.070,0.010 | ✅ 0.221,0.317,0.040,0.010 |
| BalanceDue Date | 2026-09-25 | ✅ 09/25/26 | ✅ 2026-09-25 | 0.88 | 1.0000 | - | 0.744,0.172,0.141,0.012 | 0.744,0.172,0.142,0.012 |
| BalanceGreaterCheck | No | ❌ - | ❌ - | 0.94 | N/A | - | 0.677,0.239,0.059,0.012 | - |
| Category | Electricity | ✅ Electricity | ✅ Electricity | 0.66 | 0.9500 | 0.368,0.137,0.114,0.018|0.569,0.028,0.154,0.024 | ✅ 0.567,0.027,0.156,0.025 | ❌ 0.567,0.027,0.215,0.025 |
| CountMeterIDs | 1 | ✅ 1 | ❌ - | 0.77 | N/A | - | 0.156,0.466,0.074,0.010 | - |
| Current Balance | 94.30 | ✅ 94.3 | ✅ 94.30 | 0.95 | 1.0000 | 0.677,0.292,0.051,0.012 | ✅ 0.677,0.292,0.051,0.012 | ✅ 0.677,0.292,0.051,0.012 |
| End Date | 2026-08-31 | ✅ 08/31/26 | ✅ 2026-08-31 | 0.89 | 1.0000 | - | 0.758,0.148,0.112,0.012 | 0.758,0.148,0.112,0.012 |
| Is_NumMeterIDsListed | No | ❌ - | ❌ - | 0.95 | N/A | - | 0.156,0.466,0.074,0.010 | - |
| Is_PrevGreaterThanCurr | - | - | - | 0.94 | N/A | - | - | - |
| Is_ValidPinCode | True | ✅ True | ✅ True | 0.93 | 1.0000 | - | 0.222,0.317,0.040,0.010 | 0.221,0.317,0.040,0.010 |
| Is_ValidState | True | ✅ True | ✅ True | 0.93 | 1.0000 | - | 0.114,0.317,0.103,0.012 | 0.192,0.317,0.025,0.010 |
| Line_Item_Charges.Charge | 78.20, 45.00, 33.20, 5.00, 3.10 | ❌ - | ✅ 78.20, 45.00, 33.20, 5.00, 3.10 | - | N/A | - | - | 0.114,0.588,0.046,0.011 |
| Line_Item_Charges.Line item Description | Energy Consumption (920 kWh at $0.085/kWh), Delivery/Distribution Charge, Supply/Generation Charge, Wyoming Energy Surcharge, Taxes & Fees | ❌ - | ✅ Energy Consumption (920 kWh at $0.085/kWh), Delivery/Distribution Charge, Supply/Generation Charge, Wyoming Energy Surcharge, Taxes & Fees | - | N/A | - | - | 0.115,0.714,0.337,0.013 |
| Meter Number | 02348719 | ❌ - | ❌ Meter #02348719 | - | 1.0000 | 0.156,0.467,0.074,0.009 | ❌ - | ❌ 0.114,0.466,0.115,0.009 |
| MeterRead.Current value | 920 | ❌ - | ✅ 920 | - | 1.0000 | 0.472,0.485,0.023,0.008 | ❌ - | ❌ 0.471,0.485,0.059,0.009 |
| MeterRead.Delta or Metered value | - | - | - | - | N/A | - | - | - |
| MeterRead.Meter ID | 02348719 | ❌ - | ❌ Meter #02348719 | - | 1.0000 | 0.156,0.467,0.074,0.009 | ❌ - | ❌ 0.114,0.466,0.115,0.009 |
| MeterRead.Previous value | - | - | - | - | N/A | - | - | - |
| MeterRead.Usage Unit | kWh | ❌ - | ✅ kWh | - | 1.0000 | 0.381,0.446,0.031,0.009 | ❌ - | ✅ 0.380,0.446,0.032,0.010 |
| Previous Balance | 112.45 | ✅ 112.45 | ✅ 112.45 | 0.91 | 1.0000 | 0.677,0.239,0.058,0.011 | ✅ 0.677,0.239,0.059,0.012 | ✅ 0.677,0.239,0.059,0.012 |
| Provider | Cedar Grove Energy | ✅ Cedar Grove Energy | ✅ Cedar Grove Energy | 0.95 | 0.9500 | 0.230,0.096,0.313,0.024 | ❌ 0.217,0.027,0.198,0.021 | ❌ 0.217,0.027,0.198,0.021 |
| StartDate | 2026-08-01 | ✅ 08/01/26 | ✅ 2026-08-01 | 0.91 | 0.9700 | - | 0.758,0.132,0.104,0.012 | 0.758,0.132,0.105,0.012 |
| Total Balance Due | 94.30 | ✅ 94.3 | ✅ 94.30 | 0.93 | 1.0000 | 0.677,0.292,0.051,0.012 | ❌ 0.677,0.323,0.057,0.013 | ✅ 0.677,0.292,0.051,0.012 |
| Usage.power factor | $0.085/kWh | ❌ - | ❌ $0.085 | - | 1.0000 | 0.361,0.715,0.090,0.013 | ❌ - | ❌ 0.114,0.548,0.046,0.011 |
| Usage.usage | 920 kWh | ❌ - | ✅ 920 kWh | - | 1.0000 | 0.114,0.485,0.569,0.020 | ❌ - | ❌ 0.471,0.485,0.059,0.009 |
| UsageMult | - | - | - | 0.93 | N/A | - | - | - |
