_Run: 2026-09-25 19:28 UTC_


## synthetic-expense-utility-water-sewer-bill-render-spanish.png

**Durations**

- bda: 30.83s extraction
- llm: 6.045s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| Account_Info.Acct_Name | - | Mariana López | Mariana López | 0.88 | 0.9800 | 0.039,0.235,0.094,0.011 | 0.039,0.235,0.094,0.011 | ✅ |
| Account_Info.Acct_No | - | 1234-5678-90 | 1234-5678-90 | 0.94 | 1.0000 | 0.829,0.067,0.107,0.009 | 0.829,0.067,0.107,0.009 | ✅ |
| Account_Info.Meter_Number | - | MTR-78543210 | MTR-78543210 | 0.91 | 0.9900 | 0.719,0.569,0.105,0.009 | 0.719,0.569,0.105,0.009 | ✅ |
| Curr_Meter_Reading | - | 68,200 | 68,200 | 0.57 | 1.0000 | 0.805,0.625,0.046,0.010 | 0.806,0.625,0.046,0.010 | 🟡 |
| Dates.Bill_From_Date | - | 07/21/2026 | 07/21/2026 | 0.72 | 0.9900 | 0.752,0.107,0.083,0.011 | 0.752,0.107,0.083,0.011 | ✅ |
| Dates.Bill_To_Date | - | 08/20/2026 | 08/20/2026 | 0.75 | 0.9900 | 0.851,0.107,0.084,0.011 | 0.852,0.108,0.084,0.011 | 🟡 |
| Dates.Billing_Date | - | 08/28/2026 | 08/28/2026 | 0.86 | 1.0000 | 0.848,0.087,0.087,0.011 | 0.849,0.087,0.087,0.010 | 🟡 |
| Dates.Due_Date | - | 09/18/2026 | 09/18/2026 | 0.82 | 1.0000 | 0.844,0.129,0.092,0.011 | 0.843,0.129,0.093,0.011 | 🟡 |
| Line_Items.Amount or Value | - | - | $22.50, $45.00, $12.75, $19.20, $4.50, $6.24 | - | N/A | - | 0.579,0.463,0.035,0.010 | ❌ |
| Line_Items.LineItemDescription | - | - | Cargo base de agua, Uso de agua, Cargo base de alcantarillado, Cargo de alcantarillado, Tarifa de aguas pluviales, Impuesto local sobre servicios públicos (6%) | - | N/A | - | 0.051,0.463,0.239,0.010 | ❌ |
| Prev_Bal | - | 88.03 | 0.00 | 0.90 | 1.0000 | 0.896,0.352,0.049,0.011 | 0.905,0.431,0.040,0.010 | ❌ |
| Prev_Meter_Reading | - | 62,200 | 62,200 | 0.65 | 1.0000 | 0.806,0.653,0.045,0.010 | 0.806,0.653,0.046,0.010 | 🟡 |
| Provider Name | - | SERVICIO DE AGUA DEL CONDADO DE HARBOR | SERVICIO DE AGUA DEL CONDADO DE HARBOR | 0.88 | 0.9800 | 0.146,0.045,0.356,0.038 | 0.442,0.798,0.254,0.010 | ❌ |
| Service_Address.Building_Line 1 | - | 214 Maple Way | 214 Maple Way | 0.61 | 1.0000 | 0.038,0.250,0.068,0.010 | 0.348,0.235,0.098,0.011 | ❌ |
| Service_Address.City | - | Pocatello | Pocatello | 0.86 | N/A | 0.038,0.264,0.062,0.010 | - | ❌ |
| Service_Address.State | - | ID | ID | 0.91 | 0.9900 | 0.106,0.264,0.013,0.009 | 0.214,0.141,0.013,0.009 | ❌ |
| Service_Address.Street | - | - | 214 Maple Way | 0.06 | 1.0000 | - | 0.348,0.235,0.098,0.011 | ❌ |
| Service_Address.Zip_Code | - | 83204 | 83204 | 0.92 | 0.9900 | 0.122,0.264,0.041,0.009 | 0.432,0.250,0.041,0.009 | ❌ |
| Tot_Amt | - | 86.47 | 86.47 | 0.92 | 1.0000 | 0.861,0.163,0.075,0.016 | 0.861,0.163,0.075,0.016 | ✅ |
| Total_Current_Charges | - | 110.19 | 110.19 | 0.79 | 1.0000 | 0.557,0.494,0.057,0.011 | 0.890,0.449,0.055,0.011 | ❌ |
| is_total_amount_greater_than_equal_to_current_charges | - | - | No | 0.24 | N/A | 0.861,0.163,0.075,0.016 | - | ❌ |
