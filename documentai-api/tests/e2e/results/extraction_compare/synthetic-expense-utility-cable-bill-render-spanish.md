# synthetic-expense-utility-cable-bill-render-spanish.png


_Run: 2026-09-30 02:19 UTC_


## Durations

- bda: 26.06s extraction
- ocr-mapping: 5.046s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384
- us.amazon.nova-pro-v1:0: $0.01587600
- bda: $0.04000000
- **total: $0.05599984**

_By Extraction Method_
- shared (preclassification): $0.00927584
- ocr-mapping extraction: $0.00672400
- primary (bda): $0.04000000
- **total: $0.05599984**


## Accuracy

_By Extracted Data_
- BDA: 70% equivalent, 70% close, 30% misses
- OCR Mapping: 50% equivalent, 50% close, 50% misses

_By Geometry_
- BDA: -
- OCR Mapping: -


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Geo | BDA Geometry | LLM Geometry |
|---|---|---|---|---|---|---|---|---|
| Account_Number | 8765 4321 0XXX XXXX | ✅ 8765 4321 0XXX XXXX | ❌ 8765 0XXX XXXX | 0.86 | 0.9200 | - | 0.266,0.268,0.162,0.008 | 0.127,0.267,0.301,0.009 |
| Balance_DueDate | 2026-09-30 | ✅ 09/30/26 | ✅ 2026-09-30 | 0.85 | 0.9900 | - | 0.779,0.080,0.171,0.010 | 0.779,0.080,0.171,0.010 |
| BillingDateBeforeDueDate | True | ✅ True | ✅ True | 0.30 | N/A | - | 0.780,0.045,0.171,0.009 | 0.780,0.045,0.171,0.009 |
| Billing_Date | 2026-09-11 | ✅ 09/11/26 | ✅ 2026-09-11 | 0.84 | 0.9900 | - | 0.780,0.045,0.171,0.009 | 0.780,0.045,0.171,0.009 |
| End_Date | 2026-07-11 | ✅ 07/11/26 | ✅ 2026-07-11 | 0.71 | 0.9900 | - | 0.871,0.063,0.074,0.008 | 0.871,0.063,0.075,0.008 |
| Line_Item_table.Amount | 72.99, 8.99, 5.00, -10.00, 49.99, -20.00, 7.00, 5.00, 0.00, -5.00, 4.28, 2.10, 2.54, 0.00 | ❌ - | ❌ $72.99, $8.99, $5.00, $10.00, $49.99, $20.00, $7.00, $5.00, $0.00, $5.00, $4.28, $2.10, $2.54, $0.00 | - | N/A | - | - | 0.912,0.223,0.036,0.009 |
| Line_Item_table.Line item | - | - | ❌ Paquete Preferred TV, Tarifa de Deportes Regionales, Grabación en la Nube (250 GB), Descuento promocional Preferred TV, Internet de alta velocidad 300 Mbps, Descuento promocional Internet, Renta de caja HD, Renta de módem/puerta de enlace Wi-Fi, Tarifa de activación (promoción), Crédito por lealtad, Impuesto sobre ventas del OK 4.5%, Tarifa de franquicia municipal Broken Arrow, Recuperación de costos de red, Ejecución de programación regional | - | N/A | - | - | 0.053,0.403,0.193,0.010 |
| Service_Address | 1234 Maple Drive, Broken Arrow, OK 74012 | ✅ 1234 Maple Drive Broken Arrow, OK 74012 | ❌ Jordan Rivera 1234 Maple Drive Broken Arrow, OK 74012 | 0.77 | N/A | - | 0.039,0.190,0.164,0.024 | 0.039,0.204,0.164,0.008 |
| Start_Date | 2026-08-12 | ✅ 08/12/26 | ✅ 2026-08-12 | 0.70 | 0.9900 | - | 0.780,0.063,0.076,0.009 | 0.780,0.063,0.075,0.009 |
| Summary_table.Amount | 98.75, -98.75, 0.00, 102.89, 102.89 | ❌ - | ❌ $98.75, $98.75, $0.00, $102.89, $102.89 | - | N/A | - | - | 0.904,0.173,0.044,0.009 |
| Summary_table.Description | Saldo anterior, Pagos recibidos – 08/25/2026, Saldo anterior, Cargos actuales, TOTAL A PAGAR | ❌ - | ❌ Saldo anterior, Pagos recibidos 08/25/2026, Saldo anterior, Cargos actuales, TOTAL A PAGAR | - | N/A | - | - | 0.601,0.192,0.192,0.010 |
