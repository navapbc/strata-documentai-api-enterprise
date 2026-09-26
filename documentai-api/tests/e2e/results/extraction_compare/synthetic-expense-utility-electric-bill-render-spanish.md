_Run: 2026-09-26 22:37 UTC_


## synthetic-expense-utility-electric-bill-render-spanish.png

**Durations**

- bda: 23.99s extraction
- llm: 8.134s extraction

**Cost**

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384 (1956 in / 27 out)
- us.amazon.nova-pro-v1:0: $0.01921520 (19435 in / 1146 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05933904**

_By Extraction Method_
- shared (preclassification): $0.00926304
- llm extraction: $0.01007600
- primary (bda): $0.04000000
- **total: $0.05933904**

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| Account Number | - | - | 1234-5678-9012 | - | 1.0000 | - | 0.853,0.068,0.095,0.008 | ❌ |
| Address.Service Address | - | 14 Maple Lane Burlington, VT 05401 | 14 Maple Lane Burlington, VT 05401 | 0.72 | N/A | 0.034,0.266,0.015,0.009 | 0.034,0.266,0.093,0.011 | ❌ |
| Address.Service address pin code | - | VT 05401 | 05401 | 0.71 | 1.0000 | 0.129,0.340,0.039,0.010 | 0.129,0.282,0.039,0.009 | ❌ |
| BalanceDue Date | - | 06/10/26 | 06/10/2026 | 0.85 | 1.0000 | 0.790,0.189,0.138,0.017 | 0.790,0.190,0.138,0.017 | 🟡 |
| BalanceGreaterCheck | - | - | - | 0.92 | N/A | - | - |  |
| Category | - | ELECTRICIDAD | Residencial R-1 | 0.43 | 0.9900 | 0.770,0.025,0.129,0.010 | 0.445,0.276,0.099,0.009 | ❌ |
| CountMeterIDs | - | 1 | 1 | 0.57 | 0.9300 | 0.445,0.314,0.091,0.009 | 0.915,0.103,0.031,0.008 | ❌ |
| Current Balance | - | 105.51 | 105.51 | 0.82 | 1.0000 | 0.583,0.623,0.045,0.010 | 0.583,0.623,0.045,0.010 | ✅ |
| End Date | - | 05/15/26 | 05/15/2026 | 0.86 | 0.9600 | 0.527,0.257,0.068,0.010 | 0.527,0.257,0.068,0.009 | 🟡 |
| Is_NumMeterIDsListed | - | - | - | 0.29 | N/A | 0.445,0.314,0.091,0.009 | - | ❌ |
| Is_PrevGreaterThanCurr | - | - | No | 0.89 | 0.9800 | 0.445,0.351,0.038,0.010 | 0.445,0.351,0.152,0.010 | ❌ |
| Is_ValidPinCode | - | True | Yes | 0.89 | 1.0000 | 0.129,0.340,0.039,0.010 | 0.129,0.282,0.039,0.009 | ❌ |
| Is_ValidState | - | True | Yes | 0.90 | 0.9900 | 0.107,0.281,0.017,0.009 | 0.567,0.057,0.016,0.009 | ❌ |
| Line_Item_Charges.Charge | - | - | 33.34 | - | 1.0000 | - | 0.588,0.497,0.041,0.010 | ❌ |
| Line_Item_Charges.Line item Description | - | - | Cargo por entrega (distribución) | - | 0.9500 | - | 0.038,0.498,0.171,0.010 | ❌ |
| Meter Number | - | - | MTR-72345678 | - | 0.9900 | - | 0.445,0.314,0.091,0.009 | ❌ |
| MeterRead.Current value | - | - | 15842kWh | - | 0.9800 | - | 0.445,0.332,0.069,0.010 | ❌ |
| MeterRead.Delta or Metered value | - | - | 521kWh | - | 0.9600 | - | 0.444,0.370,0.050,0.009 | ❌ |
| MeterRead.Meter ID | - | - | MTR-72345678 | - | 0.9900 | - | 0.445,0.314,0.091,0.009 | ❌ |
| MeterRead.Previous value | - | - | 15321kWh | - | 0.9800 | - | 0.445,0.351,0.069,0.010 | ❌ |
| MeterRead.Usage Unit | - | - | kWh | - | 0.9800 | - | 0.488,0.332,0.026,0.008 | ❌ |
| Previous Balance | - | 118.74 | 118.74 | 0.68 | 1.0000 | 0.085,0.191,0.051,0.011 | 0.085,0.191,0.051,0.011 | ✅ |
| Provider | - | Cedar Grove Energy | Cedar Grove Energy | 0.89 | 1.0000 | 0.147,0.024,0.237,0.046 | 0.647,0.859,0.140,0.012 | ❌ |
| StartDate | - | 04/15/26 | 04/15/2026 | 0.85 | 0.9600 | 0.444,0.257,0.068,0.009 | 0.444,0.257,0.069,0.009 | 🟡 |
| Total Balance Due | - | 134.28 | 134.28 | 0.93 | 1.0000 | 0.611,0.188,0.098,0.019 | 0.612,0.188,0.098,0.019 | 🟡 |
| Usage.power factor | - | - | - | - | N/A | - | - |  |
| Usage.usage | - | - | 521 kWh | - | 0.9600 | - | 0.444,0.370,0.050,0.009 | ❌ |
| UsageMult | - | - | - | 0.89 | N/A | - | - |  |
