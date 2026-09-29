# synthetic-expense-utility-electric-bill-render-spanish.png


_Run: 2026-09-29 19:58 UTC_


## Durations

- bda: 25.13s extraction
- ocr-mapping: 10.858s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384 (1956 in / 27 out)
- us.amazon.nova-pro-v1:0: $0.01999840 (19606 in / 1348 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.06012224**

_By Extraction Method_
- shared (preclassification): $0.00927584
- ocr-mapping extraction: $0.01084640
- primary (bda): $0.04000000
- **total: $0.06012224**


## Accuracy
- BDA: 44% equivalent, 44% close, 56% misses
- OCR Mapping: 88% equivalent, 88% close, 12% misses


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| Account Number | 1234-5678-9012 | ❌ - | ✅ 1234-5678-9012 | - | 1.0000 | - | 0.853,0.068,0.095,0.008 | ❌ |
| Address.Service Address | 14 Maple Lane, Burlington, VT 05401 | ✅ 14 Maple Lane Burlington, VT 05401 | ✅ 14 Maple Lane, Burlington, VT 05401 | 0.75 | N/A | 0.034,0.324,0.135,0.027 | 0.034,0.266,0.093,0.011 | ❌ |
| Address.Service address pin code | 05401 | ❌ VT 05401 | ✅ 05401 | 0.73 | 1.0000 | 0.129,0.340,0.039,0.010 | 0.129,0.282,0.039,0.009 | ❌ |
| BalanceDue Date | 2026-06-10 | ✅ 06/10/26 | ✅ 2026-06-10 | 0.85 | 1.0000 | 0.790,0.190,0.138,0.017 | 0.790,0.190,0.138,0.017 | ✅ |
| BalanceGreaterCheck | Yes | ❌ - | ❌ - | 0.92 | N/A | - | - |  |
| Category | Electricidad | ✅ ELECTRICIDAD | ❌ Residencial R-1 | 0.47 | 0.9900 | 0.769,0.025,0.130,0.010 | 0.445,0.276,0.099,0.009 | ❌ |
| CountMeterIDs | 1 | ✅ 1 | ✅ 1 | 0.48 | 0.9300 | 0.445,0.314,0.091,0.009 | 0.915,0.103,0.031,0.008 | ❌ |
| Current Balance | 134.28 | ❌ 105.51 | ❌ 105.51 | 0.82 | 1.0000 | 0.583,0.623,0.045,0.010 | 0.583,0.623,0.045,0.010 | ✅ |
| End Date | 2026-05-15 | ✅ 05/15/26 | ✅ 2026-05-15 | 0.86 | 0.9600 | 0.527,0.257,0.068,0.010 | 0.527,0.257,0.068,0.009 | 🟡 |
| Is_NumMeterIDsListed | - | - | - | 0.28 | N/A | 0.445,0.314,0.091,0.009 | - | ❌ |
| Is_PrevGreaterThanCurr | No | ❌ - | ✅ False | 0.89 | 0.9800 | 0.445,0.351,0.038,0.010 | 0.445,0.332,0.151,0.010 | ❌ |
| Is_ValidPinCode | True | ✅ True | ✅ True | 0.90 | 1.0000 | 0.129,0.340,0.039,0.010 | 0.129,0.282,0.039,0.009 | ❌ |
| Is_ValidState | True | ✅ True | ✅ True | 0.91 | 0.9900 | 0.107,0.340,0.017,0.009 | 0.567,0.057,0.016,0.009 | ❌ |
| Line_Item_Charges.Charge | 33.34, 51.32, 12.00, 1.04, 5.86, 1.95 | ❌ - | ✅ 33.34, 51.32, 12.00, 1.04, 5.86, 1.95 | - | N/A | - | 0.595,0.597,0.034,0.010 | ❌ |
| Line_Item_Charges.Line item Description | Cargo por entrega (distribución), Cargo por suministro (generación), Cargo básico de servicio, Ajuste de energía renovable, Impuesto estatal sobre ventas (6.000%), Impuesto municipal sobre energía (2.000%) | ❌ - | ✅ Cargo por entrega (distribución), Cargo por suministro (generación), Cargo básico de servicio, Ajuste de energía renovable, Impuesto estatal sobre ventas (6.000%), Impuesto municipal sobre energía (2.000%) | - | N/A | - | 0.038,0.598,0.231,0.010 | ❌ |
| Meter Number | MTR-72345678 | ❌ - | ✅ MTR-72345678 | - | 0.9900 | - | 0.445,0.314,0.091,0.009 | ❌ |
| MeterRead.Current value | 15842 | ❌ - | ✅ 15842 | - | 0.9800 | - | 0.445,0.332,0.151,0.010 | ❌ |
| MeterRead.Delta or Metered value | 521 | ❌ - | ✅ 521 | - | 0.9600 | - | 0.444,0.370,0.050,0.009 | ❌ |
| MeterRead.Meter ID | MTR-72345678 | ❌ - | ✅ MTR-72345678 | - | 0.9900 | - | 0.445,0.314,0.091,0.009 | ❌ |
| MeterRead.Previous value | 15321 | ❌ - | ✅ 15321 | - | 0.9800 | - | 0.445,0.351,0.152,0.010 | ❌ |
| MeterRead.Usage Unit | kWh | ❌ - | ✅ kWh | - | 0.9800 | - | 0.488,0.332,0.026,0.008 | ❌ |
| Previous Balance | 118.74 | ✅ 118.74 | ✅ 118.74 | 0.63 | 1.0000 | 0.085,0.191,0.051,0.011 | 0.085,0.191,0.051,0.011 | ✅ |
| Provider | Cedar Grove Energy | ✅ Cedar Grove Energy | ✅ Cedar Grove Energy | 0.90 | 1.0000 | 0.147,0.024,0.237,0.046 | 0.647,0.859,0.140,0.012 | ❌ |
| StartDate | 2026-04-15 | ✅ 04/15/26 | ✅ 2026-04-15 | 0.86 | 0.9600 | 0.444,0.257,0.068,0.009 | 0.444,0.257,0.069,0.009 | 🟡 |
| Total Balance Due | 134.28 | ✅ 134.28 | ✅ 134.28 | 0.93 | 1.0000 | 0.611,0.188,0.098,0.019 | 0.612,0.188,0.098,0.019 | 🟡 |
| Usage.power factor | - | - | - | - | N/A | - | - |  |
| Usage.usage | 521 kWh | ❌ - | ✅ 521 kWh | - | 0.9600 | - | 0.444,0.370,0.050,0.009 | ❌ |
| UsageMult | - | - | - | 0.90 | N/A | - | - |  |
