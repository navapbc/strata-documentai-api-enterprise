# synthetic-expense-utility-cable-bill-render-spanish.png


_Run: 2026-09-28 18:36 UTC_


## Durations

- bda: 23.2s extraction
- llm: 2.632s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384 (1956 in / 27 out)
- us.amazon.nova-pro-v1:0: $0.01389600 (14914 in / 614 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05401984**

_By Extraction Method_
- shared (preclassification): $0.00933024
- llm extraction: $0.00468960
- primary (bda): $0.04000000
- **total: $0.05401984**


## Accuracy
- BDA: 20% exact, 30% loose, 70% misses
- LLM: 0% exact, 10% loose, 90% misses


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| Account_Number | 8765 4321 0XXX XXXX | ✅ 8765 4321 0XXX XXXX | ❌ 8765 0XXX XXXX | 0.86 | 0.9200 | 0.266,0.268,0.162,0.008 | 0.127,0.267,0.301,0.009 | ❌ |
| Balance_DueDate | 2026-09-30 | ❌ 09/30/26 | ❌ 30 de septiembre de 2026 | 0.85 | 0.9900 | 0.779,0.080,0.171,0.010 | 0.779,0.080,0.171,0.010 | ✅ |
| BillingDateBeforeDueDate | True | ✅ True | 🟡 Yes | 0.30 | N/A | 0.780,0.045,0.171,0.009 | 0.780,0.045,0.171,0.009 | ✅ |
| Billing_Date | 2026-09-11 | ❌ 09/11/26 | ❌ 11 de septiembre de 2026 | 0.84 | 0.9900 | 0.780,0.045,0.171,0.009 | 0.780,0.045,0.171,0.009 | ✅ |
| End_Date | 2026-07-11 | ❌ 07/11/26 | ❌ 11/07/2026 | 0.71 | 0.9900 | 0.871,0.063,0.074,0.008 | 0.871,0.063,0.075,0.008 | 🟡 |
| Line_Item_table.Amount | 72.99, 8.99, 5.00, -10.00, 49.99, -20.00, 7.00, 5.00, 0.00, -5.00, 4.28, 2.10, 2.54, 0.00 | ❌ - | ❌ - | - | - | - | - |  |
| Service_Address | 1234 Maple Drive, Broken Arrow, OK 74012 | 🟡 1234 Maple Drive Broken Arrow, OK 74012 | ❌ Jordan Rivera 1234 Maple Drive Broken Arrow, OK 74012 | 0.77 | N/A | 0.039,0.190,0.164,0.024 | 0.039,0.204,0.164,0.008 | ❌ |
| Start_Date | 2026-08-12 | ❌ 08/12/26 | ❌ 12/08/2026 | 0.70 | 0.9900 | 0.780,0.063,0.076,0.009 | 0.780,0.063,0.075,0.009 | 🟡 |
| Summary_table.Amount | 98.75, -98.75, 0.00, 102.89, 102.89 | ❌ - | ❌ $102.89 | - | 1.0000 | - | 0.896,0.242,0.052,0.009 | ❌ |
| Summary_table.Description | Saldo anterior, Pagos recibidos – 08/25/2026, Saldo anterior, Cargos actuales, TOTAL A PAGAR | ❌ - | ❌ TOTAL A PAGAR | - | 0.9900 | - | 0.599,0.270,0.123,0.009 | ❌ |
