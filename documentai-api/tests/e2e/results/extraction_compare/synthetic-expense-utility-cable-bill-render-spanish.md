_Run: 2026-09-25 19:27 UTC_


## synthetic-expense-utility-cable-bill-render-spanish.png

**Durations**

- bda: 24.89s extraction
- llm: 2.105s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| Account_Number | - | 8765 4321 0XXX XXXX | 8765 0XXX XXXX | 0.86 | 0.9200 | 0.266,0.268,0.162,0.008 | 0.127,0.267,0.301,0.009 | ❌ |
| Balance_DueDate | - | 09/30/26 | 30 de septiembre de 2026 | 0.85 | 0.9900 | 0.779,0.080,0.171,0.010 | 0.779,0.080,0.171,0.010 | ✅ |
| BillingDateBeforeDueDate | - | True | Yes | 0.30 | N/A | 0.780,0.045,0.171,0.009 | 0.780,0.045,0.171,0.009 | ✅ |
| Billing_Date | - | 09/11/26 | 11 de septiembre de 2026 | 0.84 | 0.9900 | 0.780,0.045,0.171,0.009 | 0.780,0.045,0.171,0.009 | ✅ |
| End_Date | - | 07/11/26 | 11/07/2026 | 0.71 | 0.9900 | 0.871,0.063,0.074,0.008 | 0.871,0.063,0.075,0.008 | 🟡 |
| Line_Item_table.Amount | - | - | $72.99 | - | 1.0000 | - | 0.479,0.355,0.044,0.009 | ❌ |
| Line_Item_table.Line item | - | - | Paquete Preferred TV | - | 1.0000 | - | 0.053,0.356,0.134,0.009 | ❌ |
| Service_Address | - | 1234 Maple Drive Broken Arrow, OK 74012 | Jordan Rivera
1234 Maple Drive
Broken Arrow, OK 74012 | 0.77 | N/A | 0.039,0.190,0.164,0.024 | 0.039,0.204,0.164,0.008 | ❌ |
| Start_Date | - | 08/12/26 | 12/08/2026 | 0.70 | 0.9900 | 0.780,0.063,0.076,0.009 | 0.780,0.063,0.075,0.009 | 🟡 |
| Summary_table.Amount | - | - | $102.89 | - | 1.0000 | - | 0.896,0.242,0.052,0.009 | ❌ |
| Summary_table.Description | - | - | TOTAL A PAGAR | - | 0.9900 | - | 0.599,0.270,0.123,0.009 | ❌ |
