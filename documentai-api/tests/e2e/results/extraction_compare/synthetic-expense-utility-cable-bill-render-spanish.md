_Run: 2026-09-26 22:36 UTC_


## synthetic-expense-utility-cable-bill-render-spanish.png

**Durations**

- bda: 37.31s extraction
- llm: 3.624s extraction

**Cost**

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384 (1956 in / 27 out)
- us.amazon.nova-pro-v1:0: $0.01567840 (14914 in / 1171 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05580224**

_By Extraction Method_
- shared (preclassification): $0.00927584
- llm extraction: $0.00652640
- primary (bda): $0.04000000
- **total: $0.05580224**

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| Account_Number | - | 8765 4321 0XXX XXXX | 8765 0XXX XXXX | 0.86 | 0.9200 | 0.266,0.268,0.162,0.008 | 0.127,0.267,0.301,0.009 | ❌ |
| Balance_DueDate | - | 09/30/26 | 30 de septiembre de 2026 | 0.85 | 0.9900 | 0.779,0.080,0.171,0.010 | 0.779,0.080,0.171,0.010 | ✅ |
| BillingDateBeforeDueDate | - | True | Yes | 0.31 | N/A | 0.780,0.045,0.171,0.009 | 0.780,0.045,0.171,0.009 | ✅ |
| Billing_Date | - | 09/11/26 | 11 de septiembre de 2026 | 0.84 | 0.9900 | 0.780,0.045,0.171,0.009 | 0.780,0.045,0.171,0.009 | ✅ |
| End_Date | - | 07/11/26 | 11/07/2026 | 0.72 | 0.9900 | 0.871,0.063,0.075,0.008 | 0.871,0.063,0.075,0.008 | ✅ |
| Line_Item_table.Amount | - | - | $72.99
$8.99
$5.00
$10.00
$49.99
$20.00
$7.00
$5.00
$0.00
$5.00
$4.28
$2.10
$2.54
$0.00 | - | N/A | - | 0.912,0.223,0.036,0.009 | ❌ |
| Service_Address | - | 1234 Maple Drive Broken Arrow, OK 74012 | Jordan Rivera
1234 Maple Drive
Broken Arrow, OK 74012 | 0.77 | N/A | 0.039,0.190,0.164,0.024 | 0.039,0.204,0.164,0.008 | ❌ |
| Start_Date | - | 08/12/26 | 12/08/2026 | 0.70 | 0.9900 | 0.780,0.063,0.076,0.009 | 0.780,0.063,0.075,0.009 | 🟡 |
| Summary_table.Amount | - | - | $0.00
$102.89
$102.89 | - | N/A | - | 0.912,0.223,0.036,0.009 | ❌ |
| Summary_table.Description | - | - | Saldo anterior
Cargos actuales
TOTAL A PAGAR | - | N/A | - | 0.599,0.270,0.123,0.009 | ❌ |
