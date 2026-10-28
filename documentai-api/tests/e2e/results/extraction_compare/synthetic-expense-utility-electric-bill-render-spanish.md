# synthetic-expense-utility-electric-bill-render-spanish.png


_Run: 2026-10-01 02:38 UTC_


## Durations

- bda: 23.73s extraction
- ocr-mapping: 9.468s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384
- us.amazon.nova-pro-v1:0: $0.01977440
- bda: $0.04000000
- **total: $0.05989824**

_By Extraction Method_
- shared (preclassification): $0.00925984
- ocr-mapping extraction: $0.01063840
- primary (bda): $0.04000000
- **total: $0.05989824**


## Accuracy

_By Extracted Data_
- BDA: 11/25 (44%) equivalent match, 11/25 (44%) close, 14 misses
- OCR Mapping: 17/25 (68%) equivalent match, 17/25 (68%) close, 8 misses

_By Bounding Box_
- BDA: 2/6 exact, 3 miss
- OCR Mapping: 1/6 exact, 2 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Bounding Box | BDA Bounding Box | LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| Account Number | 1234-5678-9012 | ❌ - | ✅ 1234-5678-9012 | - | 1.0000 | - | - | 0.853,0.068,0.095,0.008 |
| Address.Service Address | 14 Maple Lane, Burlington, VT 05401 | ✅ 14 Maple Lane Burlington, VT 05401 | ✅ 14 Maple Lane, Burlington, VT 05401 | 0.72 | N/A | - | 0.034,0.266,0.015,0.009 | 0.034,0.266,0.093,0.011 |
| Address.Service address pin code | 05401 | ❌ VT 05401 | ❌ - | 0.72 | N/A | - | 0.129,0.340,0.039,0.010 | - |
| BalanceDue Date | 2026-06-10 | ✅ 06/10/26 | ✅ 2026-06-10 | 0.85 | 1.0000 | - | 0.790,0.189,0.138,0.017 | 0.790,0.190,0.138,0.017 |
| BalanceGreaterCheck | Yes | ❌ - | ❌ - | 0.92 | N/A | - | - | - |
| Category | Electricidad | ✅ ELECTRICIDAD | ❌ Residencial R-1 | 0.43 | 0.9900 | 0.793,0.025,0.105,0.009 | ✅ 0.770,0.025,0.129,0.010 | ❌ 0.445,0.276,0.099,0.009 |
| CountMeterIDs | 1 | ✅ 1 | ❌ - | 0.57 | N/A | - | 0.445,0.314,0.091,0.009 | - |
| Current Balance | 134.28 | ❌ 105.51 | ❌ 105.51 | 0.82 | 1.0000 | - | 0.583,0.623,0.045,0.010 | 0.583,0.623,0.045,0.010 |
| End Date | 2026-05-15 | ✅ 05/15/26 | ✅ 2026-05-15 | 0.86 | 0.9600 | 0.527,0.257,0.064,0.009 | ✅ 0.527,0.257,0.068,0.010 | ✅ 0.527,0.257,0.068,0.009 |
| Is_NumMeterIDsListed | - | - | - | 0.29 | N/A | - | 0.445,0.314,0.091,0.009 | - |
| Is_PrevGreaterThanCurr | No | ❌ - | ❌ - | 0.89 | N/A | - | 0.445,0.351,0.038,0.010 | - |
| Is_ValidPinCode | True | ✅ True | ❌ - | 0.89 | N/A | - | 0.129,0.340,0.039,0.010 | - |
| Is_ValidState | True | ✅ True | ❌ - | 0.90 | N/A | - | 0.107,0.281,0.017,0.009 | - |
| Line_Item_Charges.Charge | 33.34, 51.32, 12.00, 1.04, 5.86, 1.95 | ❌ - | ✅ 33.34, 51.32, 12.00, 1.04, 5.86, 1.95 | - | N/A | - | - | 0.588,0.497,0.041,0.010 |
| Line_Item_Charges.Line item Description | Cargo por entrega (distribución), Cargo por suministro (generación), Cargo básico de servicio, Ajuste de energía renovable, Impuesto estatal sobre ventas (6.000%), Impuesto municipal sobre energía (2.000%) | ❌ - | ✅ Cargo por entrega (distribución), Cargo por suministro (generación), Cargo básico de servicio, Ajuste de energía renovable, Impuesto estatal sobre ventas (6.000%), Impuesto municipal sobre energía (2.000%) | - | N/A | - | - | 0.038,0.578,0.210,0.010 |
| Meter Number | MTR-72345678 | ❌ - | ✅ MTR-72345678 | - | 0.9900 | - | - | 0.445,0.314,0.091,0.009 |
| MeterRead.Current value | 15842 | ❌ - | ✅ 15842 | - | 0.9800 | 0.444,0.333,0.039,0.009 | ❌ - | 🟡 0.445,0.332,0.069,0.010 |
| MeterRead.Delta or Metered value | 521 | ❌ - | ✅ 521 | - | 0.9600 | - | - | 0.444,0.370,0.050,0.009 |
| MeterRead.Meter ID | MTR-72345678 | ❌ - | ✅ MTR-72345678 | - | 0.9900 | - | - | 0.445,0.314,0.091,0.009 |
| MeterRead.Previous value | 15321 | ❌ - | ✅ 15321 | - | 0.9800 | 0.444,0.351,0.037,0.010 | ❌ - | 🟡 0.445,0.351,0.069,0.010 |
| MeterRead.Usage Unit | kWh | ❌ - | ✅ kWh | - | 0.9800 | - | - | 0.488,0.332,0.026,0.008 |
| Previous Balance | 118.74 | ✅ 118.74 | ✅ 118.74 | 0.68 | 1.0000 | - | 0.085,0.191,0.051,0.011 | 0.085,0.191,0.051,0.011 |
| Provider | Cedar Grove Energy | ✅ Cedar Grove Energy | ✅ Cedar Grove Energy | 0.89 | 1.0000 | - | 0.147,0.024,0.237,0.046 | 0.647,0.859,0.140,0.012 |
| StartDate | 2026-04-15 | ✅ 04/15/26 | ✅ 2026-04-15 | 0.85 | 0.9600 | 0.444,0.257,0.150,0.009 | 🟡 0.444,0.257,0.068,0.009 | 🟡 0.444,0.257,0.069,0.009 |
| Total Balance Due | 134.28 | ✅ 134.28 | ✅ 134.28 | 0.93 | 1.0000 | - | 0.611,0.188,0.098,0.019 | 0.612,0.188,0.098,0.019 |
| Usage.power factor | - | - | - | - | N/A | - | - | - |
| Usage.usage | 521 kWh | ❌ - | ✅ 521 kWh | - | 0.9600 | 0.033,0.366,0.903,0.012 | ❌ - | ❌ 0.444,0.370,0.050,0.009 |
| UsageMult | - | - | - | 0.90 | N/A | - | - | - |
