_Run: 2026-09-25 16:56 UTC_


## synthetic-expense-dependent-care-render.pdf

**Durations**

- bda: 22.72s extraction
- llm: 2s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| amount_paid | - | 1000 | 1000.00 | 0.95 | 1.0000 | 0.733,0.782,0.085,0.015 | 0.733,0.783,0.085,0.014 | 🟡 |
| balance_due | - | 1000 | 1000.00 | 0.95 | 1.0000 | 0.733,0.820,0.085,0.015 | 0.733,0.783,0.085,0.014 | ❌ |
| dependent_names | - | - | Elliot Morgan | - | 1.0000 | - | 0.195,0.361,0.105,0.014 | ❌ |
| document_type | - | Dependent Care Expense Statement | Dependent Care Expense Statement | 0.84 | 1.0000 | 0.213,0.179,0.250,0.026 | 0.213,0.179,0.562,0.026 | ❌ |
| payment_amount | - | 2000 | 2000.00 | 0.25 | 1.0000 | 0.733,0.745,0.085,0.015 | 0.733,0.745,0.085,0.015 | ✅ |
| payment_frequency | - | Weekly | Weekly | 0.92 | 1.0000 | 0.512,0.445,0.057,0.014 | 0.512,0.445,0.057,0.014 | ✅ |
| provider_address | - | 485 Maple Avenue, Providence, RI 02903 | 485 Maple Avenue, Providence, RI 02903 | 0.91 | 1.0000 | 0.249,0.090,0.308,0.014 | 0.249,0.090,0.308,0.014 | ✅ |
| provider_name | - | Bright Horizons Early Learning Center | Bright Horizons Early Learning Center | 0.89 | 1.0000 | 0.213,0.053,0.425,0.019 | 0.213,0.053,0.425,0.019 | ✅ |
| service_end_date | - | 2026-08-30 | 2026-08-30 | 0.76 | 1.0000 | 0.617,0.650,0.073,0.013 | 0.194,0.446,0.103,0.014 | ❌ |
| service_start_date | - | 2026-08-03 | 2026-08-03 | 0.64 | 1.0000 | 0.194,0.446,0.102,0.014 | 0.194,0.446,0.103,0.014 | 🟡 |
| statement_date | - | 2026-09-05 | 2026-09-05 | 0.91 | 1.0000 | 0.720,0.076,0.094,0.012 | 0.720,0.076,0.094,0.012 | ✅ |
