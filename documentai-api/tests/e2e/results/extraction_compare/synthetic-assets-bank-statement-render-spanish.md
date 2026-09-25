_Run: 2026-09-25 19:25 UTC_


## synthetic-assets-bank-statement-render-spanish.png

**Durations**

- bda: 48.11s extraction
- llm: 17.773s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_holder_address | - | 217 Magnolia Circle Apt 4B Mobile, AL 36604 | 217 Magnolia Circle Apt 4B
Mobile, AL 36604 | 0.73 | 1.0000 | 0.045,0.198,0.202,0.027 | 0.045,0.199,0.202,0.012 | ❌ |
| account_holder_name | - | María Elena Vásquez | María Elena Vásquez | 0.75 | 0.9500 | 0.045,0.182,0.156,0.011 | 0.045,0.182,0.156,0.011 | ✅ |
| account_number | - | 7421 | 7421 | 0.90 | 0.9300 | 0.705,0.179,0.035,0.009 | 0.705,0.179,0.034,0.009 | 🟡 |
| account_summary.summary_amount | - | - | 2150.00, 3900.00, 3198.00, 0.00, 2852.00 | - | N/A | - | 0.360,0.390,0.080,0.011 | ❌ |
| account_summary.summary_desc | - | - | Saldo Inicial (01/08/2026), Depósitos / Créditos Totales, Retiros / Débitos Totales, Cargos por Servicio, Saldo Final (31/08/2026) | - | N/A | - | 0.055,0.328,0.146,0.011 | ❌ |
| account_type | - | Cuenta de Cheques Personal | Cuenta de Cheques Personal | 0.80 | 1.0000 | 0.711,0.311,0.205,0.011 | 0.711,0.311,0.205,0.011 | ✅ |
| bank_name | - | Riverstone Community Bank | Riverstone Community Bank | 0.75 | 1.0000 | 0.137,0.064,0.253,0.040 | 0.711,0.364,0.208,0.011 | ❌ |
| branch_transit_number | - | 091215663 | 091215663 | 0.46 | 1.0000 | 0.711,0.346,0.084,0.009 | 0.711,0.346,0.085,0.010 | 🟡 |
| statement_end_date | - | 08/31/2026 | 31 de agosto de 2026 | 0.73 | 0.9900 | 0.824,0.124,0.139,0.010 | 0.688,0.124,0.275,0.010 | ❌ |
| statement_start_date | - | 08/01/2026 | 01 de agosto de 2026 | 0.63 | 0.9900 | 0.669,0.124,0.140,0.010 | 0.669,0.124,0.295,0.010 | ❌ |
| transaction_details.balance | - | - | 4025.00, 5900.00, 6050.00, 4291.10, 3331.70, 2852.00 | - | N/A | - | 0.360,0.390,0.080,0.011 | ❌ |
| transaction_details.date | - | - | 08/05/2026, 08/19/2026, 08/28/2026, 08/10/2026, 08/15/2026, 08/27/2026 | - | N/A | - | 0.054,0.687,0.084,0.009 | ❌ |
| transaction_details.deposits | - | - | 1875.00, 1875.00, 150.00, 0.00, 0.00, 0.00 | - | N/A | - | 0.397,0.364,0.042,0.011 | ❌ |
| transaction_details.description | - | - | DEPÓSITO: Sueldo Southern Gulf Logistics, DEPÓSITO: Sueldo Southern Gulf Logistics, DEPÓSITO: Reembolso de Capacitación, DÉBITO: Pago de Renta - Magnolia Apartments, DÉBITO: Servicios Públicos Alabama Power, DÉBITO: Compra Walmart Supercenter | - | N/A | - | 0.233,0.630,0.185,0.011 | ❌ |
| transaction_details.withdrawals | - | - | 0.00, 0.00, 0.00, 1758.90, 959.40, 479.70 | - | N/A | - | 0.719,0.686,0.060,0.011 | ❌ |
