_Run: 2026-09-25 19:28 UTC_


## synthetic-expense-utility-electric-bill-render-spanish.png

**Durations**

- bda: 24.74s extraction
- llm: 7.343s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| Account Number | - | - | 1234-5678-9012 | - | 1.0000 | - | 0.853,0.068,0.095,0.008 | ❌ |
| Address.Service Address | - | 14 Maple Lane Burlington, VT 05401 | 14 Maple Lane Burlington, VT 05401 | 0.72 | N/A | 0.034,0.266,0.015,0.009 | 0.034,0.266,0.093,0.011 | ❌ |
| Address.Service address pin code | - | VT 05401 | - | 0.72 | - | 0.129,0.340,0.039,0.010 | - | ❌ |
| BalanceDue Date | - | 06/10/26 | 06/10/2026 | 0.85 | 1.0000 | 0.790,0.189,0.138,0.017 | 0.790,0.190,0.138,0.017 | 🟡 |
| BalanceGreaterCheck | - | - | - | 0.92 | - | - | - |  |
| Category | - | ELECTRICIDAD | Residencial R-1 | 0.43 | 0.9900 | 0.770,0.025,0.129,0.010 | 0.445,0.276,0.099,0.009 | ❌ |
| CountMeterIDs | - | 1 | - | 0.57 | - | 0.445,0.314,0.091,0.009 | - | ❌ |
| Current Balance | - | 105.51 | 105.51 | 0.82 | 1.0000 | 0.583,0.623,0.045,0.010 | 0.583,0.623,0.045,0.010 | ✅ |
| End Date | - | 05/15/26 | 05/15/2026 | 0.86 | 0.9600 | 0.527,0.257,0.068,0.010 | 0.527,0.257,0.068,0.009 | 🟡 |
| Is_NumMeterIDsListed | - | - | - | 0.29 | - | 0.445,0.314,0.091,0.009 | - | ❌ |
| Is_PrevGreaterThanCurr | - | - | - | 0.89 | - | 0.445,0.351,0.038,0.010 | - | ❌ |
| Is_ValidPinCode | - | True | - | 0.89 | - | 0.129,0.340,0.039,0.010 | - | ❌ |
| Is_ValidState | - | True | - | 0.90 | - | 0.107,0.281,0.017,0.009 | - | ❌ |
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
| Usage.usage | - | - | 521 kWh | - | 0.9600 | - | 0.444,0.370,0.050,0.009 | ❌ |
| UsageMult | - | - | - | 0.90 | - | - | - |  |
