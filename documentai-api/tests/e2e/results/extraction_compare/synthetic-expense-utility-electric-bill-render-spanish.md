_Run: 2026-09-25 16:56 UTC_


## synthetic-expense-utility-electric-bill-render-spanish.png

**Durations**

- bda: 38.44s extraction
- llm: 10.976s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| Account Number | - | - | 1234-5678-9012 | - | 1.0000 | - | 0.853,0.068,0.095,0.008 | ❌ |
| Address.Service Address | - | 14 Maple Lane Burlington, VT 05401 | 14 Maple Lane
Burlington, VT 05401 | 0.75 | N/A | 0.034,0.324,0.135,0.027 | 0.034,0.266,0.093,0.011 | ❌ |
| Address.Service address pin code | - | VT 05401 | 05401 | 0.73 | 1.0000 | 0.129,0.340,0.039,0.010 | 0.129,0.282,0.039,0.009 | ❌ |
| BalanceDue Date | - | 06/10/26 | 06/10/2026 | 0.85 | 1.0000 | 0.790,0.190,0.138,0.017 | 0.790,0.190,0.138,0.017 | ✅ |
| BalanceGreaterCheck | - | - | No | 0.92 | N/A | - | - |  |
| Category | - | ELECTRICIDAD | Residencial R-1 | 0.47 | 0.9900 | 0.769,0.025,0.130,0.010 | 0.445,0.276,0.099,0.009 | ❌ |
| CountMeterIDs | - | 1 | 1 | 0.49 | N/A | 0.445,0.314,0.091,0.009 | - | ❌ |
| Current Balance | - | 105.51 | 105.51 | 0.82 | 1.0000 | 0.583,0.623,0.045,0.010 | 0.583,0.623,0.045,0.010 | ✅ |
| End Date | - | 05/15/26 | 05/15/2026 | 0.86 | 0.9600 | 0.527,0.257,0.068,0.010 | 0.527,0.257,0.068,0.009 | 🟡 |
| Is_NumMeterIDsListed | - | - | No | 0.28 | N/A | 0.445,0.314,0.091,0.009 | - | ❌ |
| Is_PrevGreaterThanCurr | - | - | No | 0.89 | N/A | 0.445,0.351,0.038,0.010 | - | ❌ |
| Is_ValidPinCode | - | True | Yes | 0.90 | 1.0000 | 0.129,0.340,0.039,0.010 | 0.129,0.282,0.039,0.009 | ❌ |
| Is_ValidState | - | True | Yes | 0.91 | 0.9900 | 0.107,0.340,0.017,0.009 | 0.567,0.057,0.016,0.009 | ❌ |
| Line_Item_Charges.Charge | - | - | 33.3451.3212.001.045.861.95 | - | N/A | - | 0.588,0.497,0.041,0.010 | ❌ |
| Line_Item_Charges.Line item Description | - | - | Cargo por entrega (distribución)
Cargo por suministro (generación)
Cargo básico de servicio
Ajuste de energía renovable
Impuesto estatal sobre ventas (6.000%)
Impuesto municipal sobre energía (2.000%) | - | N/A | - | 0.038,0.578,0.210,0.010 | ❌ |
| Meter Number | - | - | MTR-72345678 | - | 0.9900 | - | 0.445,0.314,0.091,0.009 | ❌ |
| MeterRead.Current value | - | - | 15842kWh | - | 0.9800 | - | 0.445,0.332,0.069,0.010 | ❌ |
| MeterRead.Delta or Metered value | - | - | 521kWh | - | 0.9600 | - | 0.444,0.370,0.050,0.009 | ❌ |
| MeterRead.Meter ID | - | - | MTR-72345678 | - | 0.9900 | - | 0.445,0.314,0.091,0.009 | ❌ |
| MeterRead.Previous value | - | - | 15321kWh | - | 0.9800 | - | 0.445,0.351,0.069,0.010 | ❌ |
| MeterRead.Usage Unit | - | - | kWh | - | 0.9800 | - | 0.488,0.332,0.026,0.008 | ❌ |
| Previous Balance | - | 118.74 | 118.74 | 0.62 | 1.0000 | 0.085,0.191,0.051,0.011 | 0.085,0.191,0.051,0.011 | ✅ |
| Provider | - | Cedar Grove Energy | - | 0.90 | - | 0.147,0.024,0.237,0.046 | - | ❌ |
| StartDate | - | 04/15/26 | 04/15/2026 | 0.86 | 0.9600 | 0.444,0.257,0.068,0.009 | 0.444,0.257,0.069,0.009 | 🟡 |
| Total Balance Due | - | 134.28 | 134.28 | 0.93 | 1.0000 | 0.612,0.188,0.098,0.019 | 0.612,0.188,0.098,0.019 | ✅ |
| Usage.power factor | - | - | 1 | - | 0.9300 | - | 0.915,0.103,0.031,0.008 | ❌ |
| Usage.usage | - | - | 521 kWh | - | 0.9600 | - | 0.444,0.370,0.050,0.009 | ❌ |
| UsageMult | - | - | 1 | 0.90 | 0.9300 | - | 0.915,0.103,0.031,0.008 | ❌ |
