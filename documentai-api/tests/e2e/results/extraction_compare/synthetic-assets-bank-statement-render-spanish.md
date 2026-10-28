# synthetic-assets-bank-statement-render-spanish.png


_Run: 2026-10-01 02:38 UTC_


## Durations

- bda: 35.58s extraction
- ocr-mapping: 16.738s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384
- us.amazon.nova-pro-v1:0: $0.01760000
- bda: $0.04000000
- **total: $0.05772384**

_By Extraction Method_
- shared (preclassification): $0.00933664
- ocr-mapping extraction: $0.00838720
- primary (bda): $0.04000000
- **total: $0.05772384**


## Accuracy

_By Extracted Data_
- BDA: 7/15 (47%) equivalent match, 7/15 (47%) close, 8 misses
- OCR Mapping: 13/15 (87%) equivalent match, 14/15 (93%) close, 1 miss

_By Bounding Box_
- BDA: 5/7 exact, 2 miss
- OCR Mapping: 1/7 exact, 5 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Bounding Box | BDA Bounding Box | LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| account_holder_address | 217 Magnolia Circle Apt 4B, Mobile, AL 36604 | ✅ 217 Magnolia Circle Apt 4B Mobile, AL 36604 | ✅ 217 Magnolia Circle Apt 4B, Mobile, AL 36604 | 0.74 | 1.0000 | - | 0.045,0.198,0.202,0.027 | 0.045,0.199,0.202,0.012 |
| account_holder_name | María Elena Vásquez | ✅ María Elena Vásquez | ✅ María Elena Vásquez | 0.75 | 0.9500 | 0.045,0.182,0.156,0.011 | ✅ 0.045,0.182,0.156,0.011 | ✅ 0.045,0.182,0.156,0.011 |
| account_number | •••• 7421 | ❌ 7421 | ❌ 7421 | 0.90 | 0.9900 | 0.706,0.180,0.033,0.008 | ✅ 0.705,0.179,0.035,0.009 | ❌ 0.491,0.179,0.079,0.009 |
| account_summary.summary_amount | 2150.00, 3900.00, 3198.00, 0.00, 2852.00 | ❌ - | ✅ 2150.00, 3900.00, 3198.00, 0.00, 2852.00 | - | N/A | - | - | 0.366,0.310,0.073,0.011 |
| account_summary.summary_desc | Saldo Inicial (01/08/2026), Depósitos / Créditos Totales, Retiros / Débitos Totales, Cargos por Servicio, Saldo Final (31/08/2026) | ❌ - | ✅ Saldo Inicial (01/08/2026), Depósitos / Créditos Totales, Retiros / Débitos Totales, Cargos por Servicio, Saldo Final (31/08/2026) | - | N/A | - | - | 0.055,0.328,0.202,0.011 |
| account_type | Cuenta de Cheques Personal | ✅ Cuenta de Cheques Personal | ✅ Cuenta de Cheques Personal | 0.80 | 1.0000 | 0.505,0.311,0.410,0.011 | ❌ 0.711,0.311,0.205,0.011 | ❌ 0.711,0.311,0.205,0.011 |
| bank_name | Riverstone Community Bank | ✅ Riverstone Community Bank | ✅ Riverstone Community Bank | 0.75 | 1.0000 | 0.506,0.362,0.413,0.016 | ❌ 0.137,0.064,0.253,0.040 | ❌ 0.711,0.364,0.208,0.011 |
| branch_transit_number | 091215663 | ✅ 091215663 | ✅ 091215663 | 0.48 | 0.9800 | 0.711,0.346,0.084,0.009 | ✅ 0.711,0.346,0.084,0.009 | ❌ 0.506,0.346,0.079,0.009 |
| statement_end_date | 2026-08-31 | ✅ 08/31/2026 | ✅ 2026-08-31 | 0.73 | 0.9900 | 0.824,0.124,0.139,0.010 | ✅ 0.824,0.124,0.139,0.010 | ❌ 0.688,0.124,0.275,0.010 |
| statement_start_date | 2026-08-01 | ✅ 08/01/2026 | ✅ 2026-08-01 | 0.63 | 0.9900 | 0.669,0.124,0.140,0.010 | ✅ 0.669,0.124,0.140,0.010 | 🟡 0.669,0.124,0.295,0.010 |
| transaction_details.balance | 4025.00, 5900.00, 6050.00, 4291.10, 3331.70, 2852.00 | ❌ - | ✅ 4025.00, 5900.00, 6050.00, 4291.10, 3331.70, 2852.00 | - | N/A | - | - | 0.360,0.390,0.080,0.011 |
| transaction_details.date | 2026-08-05, 2026-08-19, 2026-08-28, 2026-08-10, 2026-08-15, 2026-08-27 | ❌ - | ✅ 2026-08-05, 2026-08-19, 2026-08-28, 2026-08-10, 2026-08-15, 2026-08-27 | - | N/A | - | - | 0.054,0.547,0.084,0.009 |
| transaction_details.deposits | 1875.00, 1875.00, 150.00, 0.00, 0.00, 0.00 | ❌ - | ✅ 1875.00, 1875.00, 150.00, 0.00, 0.00, 0.00 | - | N/A | - | - | 0.397,0.364,0.042,0.011 |
| transaction_details.description | DEPÓSITO: Sueldo – Southern Gulf Logistics, DEPÓSITO: Sueldo – Southern Gulf Logistics, DEPÓSITO: Reembolso de Capacitación, DÉBITO: Pago de Renta – Magnolia Apartments, DÉBITO: Servicios Públicos – Alabama Power, DÉBITO: Compra – Walmart Supercenter | ❌ - | 🟡 DEPÓSITO: Sueldo Southern Gulf Logistics, DEPÓSITO: Sueldo Southern Gulf Logistics, DEPÓSITO: Reembolso de Capacitación, DÉBITO: Pago de Renta - Magnolia Apartments, DÉBITO: Servicios Públicos Alabama Power, DÉBITO: Compra Walmart Supercenter | - | N/A | - | - | 0.233,0.630,0.273,0.011 |
| transaction_details.withdrawals | 0.00, 0.00, 0.00, 1758.90, 959.40, 479.70 | ❌ - | ✅ 0.00, 0.00, 0.00, 1758.90, 959.40, 479.70 | - | N/A | - | - | 0.397,0.364,0.042,0.011 |
