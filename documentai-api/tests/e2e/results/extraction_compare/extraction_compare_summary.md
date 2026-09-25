# Extraction Compare Results

_Run: 2026-09-25 17:00 UTC_


## synthetic-assets-bank-statement-render-spanish.png

**Durations**

- bda: 21.6s extraction
- llm: 20.012s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_holder_address | - | 217 Magnolia Circle Apt 4B Mobile, AL 36604 | 217 Magnolia Circle Apt 4B, Mobile, AL 36604 | 0.74 | 1.0000 | 0.045,0.198,0.202,0.027 | 0.045,0.199,0.202,0.012 | ❌ |
| account_holder_name | - | María Elena Vásquez | María Elena Vásquez | 0.75 | 0.9500 | 0.045,0.182,0.156,0.011 | 0.045,0.182,0.156,0.011 | ✅ |
| account_number | - | 7421 | 7421 | 0.90 | 0.9900 | 0.705,0.179,0.035,0.009 | 0.491,0.179,0.079,0.009 | ❌ |
| account_summary.summary_amount | - | - | 2150.00, 3900.00, 3198.00, 0.00, 2852.00 | - | N/A | - | 0.366,0.310,0.073,0.011 | ❌ |
| account_summary.summary_desc | - | - | Saldo Inicial (01/08/2026), Depósitos / Créditos Totales, Retiros / Débitos Totales, Cargos por Servicio, Saldo Final (31/08/2026) | - | N/A | - | 0.055,0.328,0.202,0.011 | ❌ |
| account_type | - | Cuenta de Cheques Personal | Cuenta de Cheques Personal | 0.80 | 1.0000 | 0.711,0.311,0.205,0.011 | 0.711,0.311,0.205,0.011 | ✅ |
| bank_name | - | Riverstone Community Bank | Riverstone Community Bank | 0.76 | 1.0000 | 0.137,0.064,0.252,0.040 | 0.711,0.364,0.208,0.011 | ❌ |
| branch_transit_number | - | 091215663 | 091215663 | 0.47 | 0.9800 | 0.711,0.346,0.084,0.009 | 0.506,0.346,0.079,0.009 | ❌ |
| statement_end_date | - | 08/31/2026 | 31/08/2026 | 0.73 | 0.9900 | 0.824,0.124,0.139,0.010 | 0.688,0.124,0.275,0.010 | ❌ |
| statement_start_date | - | 08/01/2026 | 01/08/2026 | 0.63 | 0.9900 | 0.669,0.124,0.140,0.010 | 0.669,0.124,0.295,0.010 | ❌ |
| transaction_details.balance | - | - | 4025.00, 5900.00, 6050.00, 4291.10, 3331.70, 2852.00 | - | N/A | - | 0.360,0.390,0.080,0.011 | ❌ |
| transaction_details.date | - | - | 08/05/2026, 08/19/2026, 08/28/2026, 08/10/2026, 08/15/2026, 08/27/2026 | - | N/A | - | 0.054,0.547,0.084,0.009 | ❌ |
| transaction_details.deposits | - | - | 1875.00, 1875.00, 150.00, 0.00, 0.00, 0.00 | - | N/A | - | 0.397,0.364,0.042,0.011 | ❌ |
| transaction_details.description | - | - | DEPÓSITO: Sueldo Southern Gulf Logistics, DEPÓSITO: Sueldo Southern Gulf Logistics, DEPÓSITO: Reembolso de Capacitación, DÉBITO: Pago de Renta - Magnolia Apartments, DÉBITO: Servicios Públicos Alabama Power, DÉBITO: Compra Walmart Supercenter | - | N/A | - | 0.233,0.630,0.273,0.011 | ❌ |
| transaction_details.withdrawals | - | - | 0.00, 0.00, 0.00, 1758.90, 959.40, 479.70 | - | N/A | - | 0.397,0.364,0.042,0.011 | ❌ |


## synthetic-assets-bank-statement-render.pdf

**Durations**

- bda: 26.86s extraction
- llm: 5.468s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_holder_address | - | 7429 Oak Crest Drive, Little Rock, AR 72205 | 7429 Oak Crest Drive, Little Rock, AR 72205 | 0.89 | 1.0000 | 0.123,0.330,0.383,0.014 | 0.123,0.330,0.383,0.012 | 🟡 |
| account_holder_name | - | Elias K. Thornton | Elias K. Thornton | 0.93 | 1.0000 | 0.124,0.306,0.151,0.013 | 0.124,0.306,0.151,0.013 | ✅ |
| account_number | - | ****5678 | ****5678 | 0.81 | 1.0000 | 0.268,0.207,0.071,0.011 | 0.134,0.207,0.205,0.011 | ❌ |
| account_summary.summary_amount | - | - | 2275.00, 4220.00, 3460.40, 0.00, 3034.60 | - | N/A | - | 0.738,0.591,0.091,0.015 | ❌ |
| account_summary.summary_desc | - | - | Beginning Balance, Total Deposits / Credits, Total Withdrawals / Debits, Fees, Ending Balance | - | N/A | - | 0.135,0.474,0.137,0.015 | ❌ |
| account_type | - | - | - | 0.91 | - | - | - |  |
| bank_name | - | Riverbend Financial Institution | Riverbend Financial Institution | 0.92 | 1.0000 | 0.228,0.045,0.212,0.049 | 0.229,0.079,0.211,0.015 | ❌ |
| branch_transit_number | - | - | - | 0.93 | - | - | - |  |
| statement_end_date | - | 08/31/2026 | 2026-08-31 | 0.75 | 1.0000 | 0.405,0.177,0.089,0.011 | 0.134,0.177,0.360,0.011 | ❌ |
| statement_start_date | - | 06/01/2026 | 2026-06-01 | 0.80 | 1.0000 | 0.291,0.177,0.088,0.011 | 0.134,0.177,0.360,0.011 | ❌ |


## synthetic-assets-bank-statement-scan.jpg

**Durations**

- bda: 26.18s extraction
- llm: 9.863s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_holder_address | - | 237 WILLOW BEND WAY BALTIMORE, MD 21224 | 237 WILLOW BEND WAY BALTIMORE, MD 21224 | 0.75 | N/A | 0.108,0.261,0.204,0.029 | 0.108,0.261,0.204,0.010 | ❌ |
| account_holder_name | - | Alex M. Thompson | Alex M. Thompson | 0.85 | N/A | 0.107,0.244,0.183,0.011 | 0.107,0.244,0.183,0.011 | ✅ |
| account_number | - | ********5342 | *******5342 | 0.58 | 1.0000 | 0.283,0.374,0.094,0.010 | 0.065,0.374,0.062,0.009 | ❌ |
| account_summary.summary_amount | - | - | 1225.00 | - | 1.0000 | - | 0.866,0.202,0.071,0.011 | ❌ |
| account_summary.summary_desc | - | - | Beginning Balance | - | 1.0000 | - | 0.577,0.203,0.135,0.012 | ❌ |
| account_type | - | Checking | Checking | 0.93 | 1.0000 | 0.283,0.357,0.068,0.012 | 0.065,0.358,0.062,0.010 | ❌ |
| bank_name | - | Harbor Community Bank | Harbor Community Bank | 0.85 | 1.0000 | 0.178,0.046,0.280,0.053 | 0.179,0.072,0.279,0.027 | ❌ |
| branch_transit_number | - | ******1250 | - | 0.76 | N/A | 0.283,0.391,0.078,0.010 | - | ❌ |
| statement_end_date | - | 08/31/2026 | August 31, 2026 | 0.73 | 1.0000 | 0.747,0.092,0.120,0.011 | 0.609,0.092,0.258,0.012 | ❌ |
| statement_start_date | - | 08/01/2026 | August 01, 2026 | 0.71 | 1.0000 | 0.609,0.092,0.119,0.012 | 0.609,0.092,0.258,0.012 | ❌ |
| transaction_details.balance | - | - | 2600.00 | - | 1.0000 | - | 0.865,0.516,0.071,0.011 | ❌ |
| transaction_details.date | - | - | 08/06/2026 | - | 1.0000 | - | 0.071,0.516,0.081,0.009 | ❌ |
| transaction_details.deposits | - | - | 1375.00 | - | 1.0000 | - | 0.560,0.516,0.071,0.011 | ❌ |
| transaction_details.description | - | - | DIRECT DEPOSIT | - | 1.0000 | - | 0.179,0.510,0.118,0.009 | ❌ |
| transaction_details.withdrawals | - | - | - | - | 0.9000 | - | 0.786,0.520,0.010,0.002 | ❌ |


## synthetic-assets-life-insurance-policy-render.pdf

**Durations**

- bda: 20.25s extraction
- llm: 1.465s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| cash_surrender_value | - | 9500 | 9500 | 0.71 | 1.0000 | 0.477,0.474,0.059,0.015 | 0.477,0.473,0.059,0.015 | 🟡 |
| death_benefit | - | 100000 | 100000 | 0.91 | 1.0000 | 0.477,0.438,0.080,0.015 | 0.477,0.438,0.080,0.015 | ✅ |
| insured_name | - | Jordan Rivera | Jordan Rivera | 0.92 | 1.0000 | 0.476,0.368,0.125,0.015 | 0.476,0.333,0.125,0.015 | ❌ |
| insurer_name | - | Northstar Life Insurance | Northstar Life Insurance Company | 0.41 | 1.0000 | 0.274,0.034,0.224,0.030 | 0.148,0.774,0.309,0.016 | ❌ |
| policy_number | - | XX-1234567-MD | XX-1234567-MD | 0.93 | 1.0000 | 0.477,0.262,0.145,0.012 | 0.477,0.262,0.145,0.012 | ✅ |
| policy_type | - | Universal Life Insurance | Universal Life Insurance | 0.89 | 1.0000 | 0.477,0.403,0.225,0.013 | 0.477,0.403,0.225,0.013 | ✅ |
| policyholder_name | - | Jordan Rivera | Jordan Rivera | 0.93 | 1.0000 | 0.476,0.333,0.125,0.015 | 0.476,0.333,0.125,0.015 | ✅ |
| premium_amount | - | 50 | 50.00 | 0.91 | 1.0000 | 0.477,0.508,0.059,0.014 | 0.477,0.508,0.059,0.014 | ✅ |
| premium_frequency | - | Monthly | Monthly | 0.71 | N/A | 0.542,0.508,0.089,0.016 | - | ❌ |
| statement_date | - | 2026-08-31 | 2026-08-31 | 0.82 | 1.0000 | 0.477,0.297,0.138,0.016 | 0.477,0.297,0.139,0.016 | 🟡 |


## synthetic-assets-life-insurance-policy-scan.jpg

**Durations**

- bda: 22.83s extraction
- llm: 5.207s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| cash_surrender_value | - | 13000 | 13000 | 0.92 | 1.0000 | 0.462,0.516,0.092,0.018 | 0.463,0.517,0.091,0.018 | 🟡 |
| death_benefit | - | 50000 | 50000 | 0.89 | 1.0000 | 0.172,0.515,0.092,0.018 | 0.172,0.515,0.092,0.018 | ✅ |
| insured_name | - | Jordan Rivera | Jordan Rivera | 0.94 | 0.9900 | 0.714,0.394,0.092,0.009 | 0.103,0.264,0.105,0.010 | ❌ |
| insurer_name | - | Northstar Life Insurance Company | Northstar Life Insurance Company | 0.83 | 1.0000 | 0.083,0.144,0.232,0.011 | 0.083,0.144,0.232,0.011 | ✅ |
| policy_number | - | NSL-78XX-45XX-9X21 | NSL-78XX-45XX-9X21 | 0.94 | 0.9800 | 0.304,0.373,0.148,0.010 | 0.304,0.373,0.148,0.010 | ✅ |
| policy_type | - | Whole Life Insurance | Whole Life Insurance | 0.91 | 1.0000 | 0.303,0.391,0.140,0.010 | 0.303,0.392,0.139,0.010 | 🟡 |
| policyholder_name | - | Jordan Rivera | Jordan Rivera | 0.95 | 0.9900 | 0.713,0.376,0.092,0.009 | 0.103,0.264,0.105,0.010 | ❌ |
| premium_amount | - | 175 | 175.00 | 0.95 | 1.0000 | 0.302,0.466,0.053,0.011 | 0.302,0.466,0.053,0.011 | ✅ |
| premium_frequency | - | Monthly | Monthly | 0.92 | 1.0000 | 0.750,0.520,0.089,0.017 | 0.303,0.448,0.053,0.012 | ❌ |
| statement_date | - | 2026-09-01 | 2026-09-01 | 0.89 | 0.9900 | 0.719,0.081,0.125,0.011 | 0.720,0.081,0.125,0.011 | 🟡 |


## synthetic-assets-trust-funds-investment-accounts-render-spanish.png

**Durations**

- bda: 21.52s extraction
- llm: 2.68s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_balance | - | 45000 | 45000.00 | 0.94 | 1.0000 | 0.866,0.327,0.083,0.011 | 0.866,0.327,0.083,0.011 | ✅ |
| account_number | - | PTC-9***-4582 | PTC-9***-4582 | 0.52 | 0.9700 | 0.258,0.284,0.104,0.009 | 0.258,0.284,0.104,0.009 | ✅ |
| asset_types | - | - | Acciones (Nacionales), Bonos (Renta Fija), Fondos Mutuos, Efectivo y Equivalentes | - | N/A | - | 0.041,0.815,0.156,0.011 | ❌ |
| beneficiary_name | - | María Isabel Rivera | María Isabel Rivera | 0.73 | 0.9500 | 0.258,0.187,0.131,0.009 | 0.258,0.187,0.131,0.009 | ✅ |
| distributions_during_period | - | 900 | (900.00) | 0.95 | 1.0000 | 0.889,0.270,0.061,0.010 | 0.889,0.270,0.061,0.010 | ✅ |
| statement_period_end | - | 2026-08-31 | 2026-08-31 | 0.72 | 1.0000 | 0.790,0.148,0.062,0.008 | 0.746,0.148,0.168,0.008 | ❌ |
| statement_period_start | - | 2026-06-01 | 2026-06-01 | 0.85 | 0.9900 | 0.271,0.410,0.121,0.010 | 0.271,0.410,0.284,0.010 | ❌ |
| trust_name | - | Fideicomiso Rivera 2019 R | Fideicomiso Rivera 2019 R | 0.93 | 0.8600 | 0.258,0.147,0.175,0.008 | 0.258,0.147,0.175,0.008 | ✅ |
| trust_type | - | Revocable (Inter Vivos) | Revocable (Inter Vivos) | 0.93 | 0.9500 | 0.258,0.167,0.153,0.010 | 0.258,0.167,0.153,0.010 | ✅ |
| trustee_name | - | Pinehurst Trust Company | Pinehurst Trust Company | 0.91 | 1.0000 | 0.258,0.264,0.174,0.010 | 0.738,0.023,0.171,0.010 | ❌ |


## synthetic-assets-trust-funds-investment-accounts-render.pdf

**Durations**

- bda: 21.89s extraction
- llm: 5.99s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_balance | - | 100000 | 100000.00 | 0.91 | 1.0000 | 0.788,0.552,0.089,0.013 | 0.788,0.552,0.090,0.012 | 🟡 |
| account_number | - | XX-XX-3456 | Acct #: XX-XX-3456 | 0.88 | 1.0000 | 0.756,0.292,0.089,0.010 | 0.702,0.292,0.144,0.010 | ❌ |
| asset_types | - | - | Equity Securities, Fixed Income Securities, Real Estate Holdings, Cash and Cash Equivalents | - | N/A | - | 0.110,0.726,0.198,0.013 | ❌ |
| beneficiary_name | - | Rivera Family Revocable Trust | Jordan A. Rivera | 0.07 | 0.9900 | 0.257,0.265,0.217,0.013 | 0.702,0.266,0.118,0.010 | ❌ |
| distributions_during_period | - | 2000 | 2000.00 | 0.92 | 1.0000 | 0.807,0.500,0.070,0.012 | 0.807,0.500,0.070,0.012 | ✅ |
| statement_period_end | - | 2026-06-30 | 2026-06-30 | 0.87 | 1.0000 | 0.833,0.167,0.079,0.010 | 0.834,0.167,0.078,0.010 | 🟡 |
| statement_period_start | - | 2026-01-01 | 2026-01-01 | 0.86 | 1.0000 | 0.734,0.167,0.076,0.010 | 0.734,0.167,0.077,0.010 | 🟡 |
| trust_name | - | Jordan A. Rivera | Rivera Family Revocable Trust | 0.29 | 1.0000 | 0.702,0.266,0.118,0.010 | 0.257,0.266,0.217,0.013 | ❌ |
| trust_type | - | Revocable Trust | Revocable Trust | 0.92 | 1.0000 | 0.257,0.292,0.116,0.010 | 0.359,0.266,0.115,0.010 | ❌ |
| trustee_name | - | Cedar Grove Trust Company | Cedar Grove Trust Company | 0.91 | 1.0000 | 0.233,0.126,0.055,0.013 | 0.093,0.125,0.303,0.017 | ❌ |


## synthetic-assets-trust-funds-investment-accounts-scan.jpg

**Durations**

- bda: 20.81s extraction
- llm: 2.041s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_balance | - | 90000 | 90000.00 | 0.95 | 1.0000 | 0.414,0.497,0.076,0.011 | 0.846,0.365,0.084,0.012 | ❌ |
| account_number | - | TR-4567-89XX | TR-4567-89XX | 0.94 | 1.0000 | 0.699,0.123,0.098,0.010 | 0.700,0.123,0.097,0.010 | 🟡 |
| asset_types | - | - | U.S. Equities, Fixed Income, Cash & Cash Equivalents, Alternative Investments | - | N/A | - | 0.053,0.845,0.082,0.009 | ❌ |
| beneficiary_name | - | Morgan Elise Dalton | Morgan Elise Dalton | 0.93 | 1.0000 | 0.647,0.310,0.132,0.011 | 0.046,0.263,0.135,0.011 | ❌ |
| distributions_during_period | - | 1800 | 1800.00 | 0.94 | 1.0000 | 0.418,0.450,0.072,0.011 | 0.871,0.397,0.060,0.010 | ❌ |
| statement_period_end | - | 2026-08-31 | 2026-08-31 | 0.85 | 1.0000 | 0.801,0.105,0.109,0.012 | 0.699,0.089,0.108,0.012 | ❌ |
| statement_period_start | - | 2026-06-01 | 2026-06-01 | 0.91 | 1.0000 | 0.699,0.107,0.089,0.010 | 0.699,0.105,0.212,0.012 | ❌ |
| trust_name | - | The Morgan E. Dalton Revocable Trust | The Morgan E. Dalton Revocable Trust | 0.90 | 1.0000 | 0.646,0.257,0.255,0.013 | 0.645,0.257,0.255,0.013 | 🟡 |
| trust_type | - | Revocable Living Trust | Revocable Living Trust | 0.94 | 1.0000 | 0.700,0.156,0.151,0.011 | 0.701,0.156,0.150,0.011 | 🟡 |
| trustee_name | - | Cedar Grove Trust Company, as Trustee | Cedar Grove Trust Company | 0.60 | 1.0000 | 0.268,0.058,0.092,0.018 | 0.646,0.292,0.193,0.010 | ❌ |


## synthetic-expense-burial-scan-corner-torn.jpg

**Durations**

- bda: 20.7s extraction
- llm: 2.166s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_balance | - | 2750 | 2750.00 | 0.93 | 1.0000 | 0.837,0.623,0.072,0.012 | 0.092,0.461,0.305,0.014 | ❌ |
| account_number | - | ***_***-7429 | ***_***-7429 | 0.28 | 0.9700 | 0.696,0.261,0.084,0.010 | 0.538,0.260,0.242,0.010 | ❌ |
| asset_types | - | - | Cash | - | 1.0000 | - | 0.092,0.461,0.208,0.011 | ❌ |
| beneficiary_name | - | Payable to Estate | Payable to Estate | 0.80 | N/A | 0.559,0.754,0.128,0.012 | 0.586,0.713,0.191,0.011 | ❌ |
| distributions_during_period | - | - | 0.00 | 0.93 | N/A | 0.579,0.412,0.041,0.011 | 0.743,0.404,0.120,0.010 | ❌ |
| statement_period_end | - | 2026-08-31 | 2026-08-31 | 0.85 | 0.9600 | 0.775,0.202,0.127,0.012 | 0.538,0.302,0.398,0.013 | ❌ |
| statement_period_start | - | 2026-01-01 | 2026-01-01 | 0.86 | 0.9600 | 0.696,0.302,0.110,0.011 | 0.538,0.302,0.398,0.013 | ❌ |
| trust_name | - | - | Irrevocable Burial Trust Account | 0.26 | 1.0000 | - | 0.697,0.240,0.222,0.010 | ❌ |
| trust_type | - | Irrevocable Burial Trust Account | Irrevocable | 0.88 | 1.0000 | 0.697,0.240,0.222,0.010 | 0.697,0.240,0.222,0.010 | ✅ |
| trustee_name | - | CEDAR GROVE BURIAL TRUST COMPANY | Cedar Grove Burial Trust Company | 0.82 | 1.0000 | 0.209,0.073,0.348,0.039 | 0.209,0.097,0.348,0.016 | ❌ |


## synthetic-expense-child-support-rendered.pdf

**Durations**

- bda: 24.97s extraction
- llm: 1.685s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| case_number | - | FC-2026-047532 | FC-2026-047532 | 0.93 | 1.0000 | 0.674,0.121,0.164,0.013 | 0.575,0.121,0.263,0.013 | ❌ |
| child_name | - | - | - | 0.94 | - | - | - |  |
| court_name | - | Fourth Judicial District Court, Missoula County | Fourth Judicial District Court, Missoula County | 0.78 | 1.0000 | 0.374,0.414,0.376,0.014 | 0.375,0.414,0.376,0.014 | 🟡 |
| effective_end_date | - | - | - | 0.02 | - | - | - |  |
| effective_start_date | - | - | - | 0.03 | - | 0.461,0.644,0.061,0.013 | - | ❌ |
| order_date | - | - | - | 0.83 | - | - | - |  |
| payer_name | - | Jordan Rivera | Jordan Rivera | 0.91 | 1.0000 | 0.325,0.252,0.114,0.011 | 0.325,0.252,0.113,0.012 | 🟡 |
| payment_amount | - | 800 | 800 | 0.93 | 1.0000 | 0.374,0.438,0.040,0.014 | 0.374,0.438,0.249,0.015 | ❌ |
| payment_frequency | - | Weekly | Weekly | 0.91 | 1.0000 | 0.373,0.464,0.145,0.015 | 0.373,0.464,0.212,0.015 | ❌ |
| payment_type | - | Child Support | - | 0.42 | - | 0.258,0.071,0.160,0.020 | - | ❌ |
| recipient_address | - | - | 1523 Aspen Ridge Drive, Helena, MT 59601 | 0.58 | 1.0000 | - | 0.326,0.306,0.355,0.015 | ❌ |
| recipient_name.first_name | - | - | - | 0.89 | - | - | - |  |
| recipient_name.last_name | - | - | - | 0.39 | - | - | - |  |
| recipient_name.middle_name | - | - | - | 0.88 | - | - | - |  |
| recipient_state | - | - | - | 0.15 | - | - | - |  |
| recipient_zip_code | - | - | - | 0.16 | - | - | - |  |


## synthetic-expense-child-support-scan.jpg

**Durations**

- bda: 27.22s extraction
- llm: 2.479s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| case_number | - | D-2022-04567-FC | D-2022-04567-FC | 0.89 | 1.0000 | 0.711,0.190,0.118,0.009 | 0.711,0.190,0.118,0.009 | ✅ |
| child_name | - | - | - | 0.91 | - | - | - |  |
| court_name | - | 2nd Judicial District Court | 2nd Judicial District Court | 0.68 | 1.0000 | 0.711,0.227,0.168,0.009 | 0.710,0.227,0.168,0.009 | 🟡 |
| effective_end_date | - | - | - | 0.90 | - | - | - |  |
| effective_start_date | - | 2022-03-22 | 03/22/2022 | 0.77 | 1.0000 | 0.356,0.361,0.073,0.009 | 0.356,0.361,0.073,0.009 | ✅ |
| order_date | - | 2022-03-15 | 03/15/2022 | 0.92 | 1.0000 | 0.711,0.208,0.073,0.009 | 0.711,0.208,0.074,0.009 | 🟡 |
| payer_name | - | Daniel R. Montoya | Daniel R. Montoya | 0.93 | 1.0000 | 0.712,0.282,0.123,0.011 | 0.711,0.282,0.123,0.011 | 🟡 |
| payment_amount | - | 500 | 500.00 | 0.89 | 1.0000 | 0.356,0.300,0.053,0.011 | 0.356,0.300,0.052,0.010 | 🟡 |
| payment_frequency | - | Weekly | Weekly | 0.89 | 1.0000 | 0.356,0.315,0.049,0.011 | 0.097,0.300,0.048,0.011 | ❌ |
| payment_type | - | Child Support | Child Support | 0.84 | 1.0000 | 0.711,0.264,0.133,0.011 | 0.711,0.264,0.134,0.011 | 🟡 |
| recipient_address | - | 123 Desert Sage Rd, Apt 4B Albuquerque, NM 87108 | 123 Desert Sage Rd, Apt 4B
Albuquerque, NM 87108 | 0.79 | 1.0000 | 0.097,0.226,0.188,0.029 | 0.098,0.226,0.186,0.011 | ❌ |
| recipient_name.first_name | - | Maria | Maria | 0.02 | 1.0000 | 0.098,0.189,0.084,0.009 | 0.098,0.189,0.039,0.009 | ❌ |
| recipient_name.last_name | - | Lopez | Lopez | 0.88 | 1.0000 | 0.186,0.189,0.043,0.011 | 0.186,0.189,0.043,0.011 | ✅ |
| recipient_name.middle_name | - | Elena | Elena | 0.28 | 1.0000 | 0.142,0.189,0.039,0.009 | 0.142,0.189,0.039,0.009 | ✅ |
| recipient_state | - | NM | NM | 0.89 | 1.0000 | 0.192,0.244,0.022,0.009 | 0.537,0.114,0.029,0.010 | ❌ |
| recipient_zip_code | - | 87108 | 87108 | 0.90 | 1.0000 | 0.222,0.244,0.041,0.009 | 0.221,0.244,0.041,0.009 | 🟡 |


## synthetic-expense-child-support-spanish-picture.png

**Durations**

- bda: 34.91s extraction
- llm: 2.874s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| case_number | - | CS-21-123456 | CS-21-123456 | 0.90 | 0.9600 | 0.476,0.248,0.086,0.008 | 0.367,0.248,0.196,0.008 | ❌ |
| child_name | - | - | - | 0.88 | - | - | - |  |
| court_name | - | Tribunal de Familia de la Ciudad de Norfolk | Tribunal de Familia de la Ciudad de Norfolk | 0.86 | 1.0000 | 0.366,0.264,0.235,0.021 | 0.366,0.264,0.235,0.008 | ❌ |
| effective_end_date | - | - | - | 0.88 | - | - | - |  |
| effective_start_date | - | 2021-05-01 | 05/01/2021 | 0.84 | 1.0000 | 0.171,0.385,0.072,0.009 | 0.068,0.385,0.174,0.009 | ❌ |
| order_date | - | 2021-05-01 | 05/01/2021 | 0.84 | 0.9900 | 0.485,0.293,0.069,0.009 | 0.366,0.293,0.189,0.008 | ❌ |
| payer_name | - | Daniel Ortega | Daniel Ortega | 0.88 | 0.9900 | 0.646,0.251,0.089,0.010 | 0.646,0.235,0.189,0.010 | ❌ |
| payment_amount | - | 450 | 450.00 | 0.73 | 1.0000 | 0.241,0.352,0.077,0.010 | 0.071,0.353,0.299,0.010 | ❌ |
| payment_frequency | - | Semanal | Semanal | 0.90 | 1.0000 | 0.208,0.369,0.054,0.008 | 0.070,0.369,0.193,0.008 | ❌ |
| payment_type | - | - | - | 0.05 | - | - | - |  |
| recipient_address | - | 4721 Willow Crossing Drive, Apt. 3B Norfolk, VA 23513 | 4721 Willow Crossing Drive, Apt. 3B, Norfolk, VA 23513 | 0.83 | 1.0000 | 0.074,0.262,0.220,0.023 | 0.074,0.263,0.220,0.010 | ❌ |
| recipient_name.first_name | - | Marisol | Marisol | 0.89 | N/A | 0.076,0.248,0.048,0.008 | 0.078,0.232,0.142,0.010 | ❌ |
| recipient_name.last_name | - | Vega | Vega | 0.84 | N/A | 0.128,0.247,0.033,0.010 | 0.078,0.232,0.142,0.010 | ❌ |
| recipient_name.middle_name | - | - | - | 0.84 | - | - | - |  |
| recipient_state | - | VA | - | 0.89 | - | 0.127,0.276,0.017,0.008 | - | ❌ |
| recipient_zip_code | - | 23513 | - | 0.89 | - | 0.149,0.276,0.039,0.008 | - | ❌ |


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


## synthetic-expense-dependent-care-scan.png

**Durations**

- bda: 29s extraction
- llm: 2.867s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| amount_paid | - | 650 | 650.00 | 0.80 | 1.0000 | 0.860,0.658,0.061,0.011 | 0.602,0.718,0.142,0.010 | ❌ |
| balance_due | - | 650 | 650.00 | 0.94 | 1.0000 | 0.868,0.743,0.065,0.012 | 0.603,0.744,0.115,0.010 | ❌ |
| dependent_names | - | - | Elliot James Morgan | - | N/A | - | 0.064,0.318,0.288,0.010 | ❌ |
| document_type | - | DEPENDENT CARE EXPENSE STATEMENT | DEPENDENT CARE EXPENSE STATEMENT | 0.87 | 1.0000 | 0.655,0.046,0.261,0.035 | 0.647,0.242,0.217,0.011 | ❌ |
| payment_amount | - | 325 | 325.00 | 0.78 | 1.0000 | 0.722,0.466,0.061,0.011 | 0.723,0.466,0.061,0.011 | 🟡 |
| payment_frequency | - | - | Weekly | 0.81 | 1.0000 | - | 0.573,0.467,0.049,0.012 | ❌ |
| provider_address | - | 321 Whispering Pines Drive Holly Springs, NC 27540 | 321 Whispering Pines Drive
Holly Springs, NC 27540 | 0.91 | N/A | 0.219,0.071,0.207,0.029 | 0.219,0.049,0.337,0.015 | ❌ |
| provider_name | - | Pine Ridge Family Learning Center | Pine Ridge Family Learning Center | 0.93 | 1.0000 | 0.219,0.049,0.336,0.015 | 0.219,0.049,0.337,0.015 | 🟡 |
| service_end_date | - | 2026-08-30 | 08/30/2026 | 0.77 | 0.9100 | 0.859,0.123,0.082,0.009 | 0.607,0.123,0.334,0.009 | ❌ |
| service_start_date | - | 2026-08-03 | 08/03/2026 | 0.79 | 0.9100 | 0.758,0.123,0.090,0.010 | 0.607,0.123,0.334,0.009 | ❌ |
| statement_date | - | 2026-09-02 | 09/02/2026 | 0.83 | 1.0000 | 0.757,0.103,0.083,0.009 | 0.607,0.103,0.233,0.009 | ❌ |


## synthetic-expense-utility-cable-bill-render-spanish.png

**Durations**

- bda: 25.16s extraction
- llm: 2.072s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| Account_Number | - | 8765 4321 0XXX XXXX | 8765 0XXX XXXX | 0.86 | 0.9200 | 0.266,0.268,0.162,0.008 | 0.127,0.267,0.301,0.009 | ❌ |
| Balance_DueDate | - | 09/30/26 | 30 de septiembre de 2026 | 0.85 | 0.9900 | 0.779,0.080,0.171,0.010 | 0.779,0.080,0.171,0.010 | ✅ |
| BillingDateBeforeDueDate | - | True | Yes | 0.31 | N/A | 0.780,0.045,0.171,0.009 | 0.780,0.045,0.171,0.009 | ✅ |
| Billing_Date | - | 09/11/26 | 11 de septiembre de 2026 | 0.84 | 0.9900 | 0.780,0.045,0.171,0.009 | 0.780,0.045,0.171,0.009 | ✅ |
| End_Date | - | 07/11/26 | 11/07/2026 | 0.72 | 0.9900 | 0.871,0.063,0.075,0.008 | 0.871,0.063,0.075,0.008 | ✅ |
| Line_Item_table.Amount | - | - | $72.99 | - | 1.0000 | - | 0.479,0.355,0.044,0.009 | ❌ |
| Service_Address | - | 1234 Maple Drive Broken Arrow, OK 74012 | Jordan Rivera
1234 Maple Drive
Broken Arrow, OK 74012 | 0.77 | N/A | 0.039,0.190,0.164,0.024 | 0.039,0.204,0.164,0.008 | ❌ |
| Start_Date | - | 08/12/26 | 12/08/2026 | 0.70 | 0.9900 | 0.780,0.063,0.076,0.009 | 0.780,0.063,0.075,0.009 | 🟡 |
| Summary_table.Amount | - | - | $102.89 | - | 1.0000 | - | 0.896,0.242,0.052,0.009 | ❌ |
| Summary_table.Description | - | - | TOTAL A PAGAR | - | 0.9900 | - | 0.599,0.270,0.123,0.009 | ❌ |


## synthetic-expense-utility-cable-bill-render.pdf

**Durations**

- bda: 27.21s extraction
- llm: 2.393s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| Account_Number | - | ACCT# 8372-XX-3498 | 8372-XX-3498 | 0.69 | 1.0000 | 0.797,0.073,0.100,0.008 | 0.797,0.073,0.099,0.008 | 🟡 |
| Balance_DueDate | - | 09/15/26 | 09/15/2026 | 0.82 | 1.0000 | 0.827,0.050,0.069,0.008 | 0.270,0.929,0.088,0.011 | ❌ |
| BillingDateBeforeDueDate | - | True | Yes | 0.39 | N/A | 0.827,0.026,0.069,0.009 | 0.707,0.026,0.050,0.008 | ❌ |
| Billing_Date | - | 08/28/26 | 08/28/2026 | 0.80 | 1.0000 | 0.827,0.026,0.069,0.009 | 0.827,0.026,0.069,0.009 | ✅ |
| End_Date | - | 08/31/26 | 08/31/2026 | 0.82 | 0.9900 | 0.764,0.203,0.122,0.013 | 0.627,0.203,0.258,0.013 | ❌ |
| Line_Item_table.Amount | - | - | $54.99 | - | 1.0000 | - | 0.413,0.600,0.044,0.011 | ❌ |
| Service_Address | - | 5127 Maplewood Drive, Lincoln, NE 68506 | 5127 Maplewood Drive, Lincoln, NE 68506 | 0.84 | 1.0000 | 0.110,0.269,0.277,0.012 | 0.110,0.269,0.276,0.012 | 🟡 |
| Start_Date | - | 08/01/26 | 08/01/2026 | 0.83 | 0.9900 | 0.627,0.203,0.124,0.013 | 0.627,0.203,0.258,0.013 | ❌ |
| Summary_table.Amount | - | - | $112.25 | - | 1.0000 | - | 0.828,0.292,0.057,0.012 | ❌ |
| Summary_table.Description | - | - | AMOUNT DUE | - | N/A | - | 0.707,0.050,0.022,0.008 | ❌ |


## synthetic-expense-utility-electric-bill-render-spanish.png

**Durations**

- bda: 38.44s extraction
- llm: 10.976s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| Account Number | - | - | 1234-5678-9012 | - | 1.0000 | - | 0.853,0.068,0.095,0.008 | ❌ |
| Address.Service Address | - | 14 Maple Lane Burlington, VT 05401 | 14 Maple Lane
Burlington, VT 05401 | 0.75 | N/A | 0.034,0.324,0.135,0.027 | 0.034,0.266,0.093,0.011 | ❌ |
| Address.Service address pin code | - | VT 05401 | 05401 | 0.73 | 1.0000 | 0.129,0.340,0.039,0.010 | 0.129,0.282,0.039,0.009 | ❌ |
| BalanceDue Date | - | 06/10/26 | 06/10/2026 | 0.85 | 1.0000 | 0.790,0.190,0.138,0.017 | 0.790,0.190,0.138,0.017 | ✅ |
| BalanceGreaterCheck | - | - | No | 0.92 | N/A | - | - |  |
| Category | - | ELECTRICIDAD | Residencial R-1 | 0.47 | 0.9900 | 0.769,0.025,0.130,0.010 | 0.445,0.276,0.099,0.009 | ❌ |
| CountMeterIDs | - | 1 | 1 | 0.49 | N/A | 0.445,0.314,0.091,0.009 | - | ❌ |
| Current Balance | - | 105.51 | 105.51 | 0.82 | 1.0000 | 0.583,0.623,0.045,0.010 | 0.583,0.623,0.045,0.010 | ✅ |
| End Date | - | 05/15/26 | 05/15/2026 | 0.86 | 0.9600 | 0.527,0.257,0.068,0.010 | 0.527,0.257,0.068,0.009 | 🟡 |
| Is_NumMeterIDsListed | - | - | No | 0.28 | N/A | 0.445,0.314,0.091,0.009 | - | ❌ |
| Is_PrevGreaterThanCurr | - | - | No | 0.89 | N/A | 0.445,0.351,0.038,0.010 | - | ❌ |
| Is_ValidPinCode | - | True | Yes | 0.90 | 1.0000 | 0.129,0.340,0.039,0.010 | 0.129,0.282,0.039,0.009 | ❌ |
| Is_ValidState | - | True | Yes | 0.91 | 0.9900 | 0.107,0.340,0.017,0.009 | 0.567,0.057,0.016,0.009 | ❌ |
| Line_Item_Charges.Charge | - | - | 33.3451.3212.001.045.861.95 | - | N/A | - | 0.588,0.497,0.041,0.010 | ❌ |
| Line_Item_Charges.Line item Description | - | - | Cargo por entrega (distribución)
Cargo por suministro (generación)
Cargo básico de servicio
Ajuste de energía renovable
Impuesto estatal sobre ventas (6.000%)
Impuesto municipal sobre energía (2.000%) | - | N/A | - | 0.038,0.578,0.210,0.010 | ❌ |
| Meter Number | - | - | MTR-72345678 | - | 0.9900 | - | 0.445,0.314,0.091,0.009 | ❌ |
| MeterRead.Current value | - | - | 15842kWh | - | 0.9800 | - | 0.445,0.332,0.069,0.010 | ❌ |
| MeterRead.Delta or Metered value | - | - | 521kWh | - | 0.9600 | - | 0.444,0.370,0.050,0.009 | ❌ |
| MeterRead.Meter ID | - | - | MTR-72345678 | - | 0.9900 | - | 0.445,0.314,0.091,0.009 | ❌ |
| MeterRead.Previous value | - | - | 15321kWh | - | 0.9800 | - | 0.445,0.351,0.069,0.010 | ❌ |
| MeterRead.Usage Unit | - | - | kWh | - | 0.9800 | - | 0.488,0.332,0.026,0.008 | ❌ |
| Previous Balance | - | 118.74 | 118.74 | 0.62 | 1.0000 | 0.085,0.191,0.051,0.011 | 0.085,0.191,0.051,0.011 | ✅ |
| Provider | - | Cedar Grove Energy | - | 0.90 | - | 0.147,0.024,0.237,0.046 | - | ❌ |
| StartDate | - | 04/15/26 | 04/15/2026 | 0.86 | 0.9600 | 0.444,0.257,0.068,0.009 | 0.444,0.257,0.069,0.009 | 🟡 |
| Total Balance Due | - | 134.28 | 134.28 | 0.93 | 1.0000 | 0.612,0.188,0.098,0.019 | 0.612,0.188,0.098,0.019 | ✅ |
| Usage.power factor | - | - | 1 | - | 0.9300 | - | 0.915,0.103,0.031,0.008 | ❌ |
| Usage.usage | - | - | 521 kWh | - | 0.9600 | - | 0.444,0.370,0.050,0.009 | ❌ |
| UsageMult | - | - | 1 | 0.90 | 0.9300 | - | 0.915,0.103,0.031,0.008 | ❌ |


## synthetic-expense-utility-electric-bill-render.pdf

**Durations**

- bda: 24.39s extraction
- llm: 32.403s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| Account Number | - | - | ****-6729 | - | 0.9900 | - | 0.782,0.085,0.065,0.010 | ❌ |
| Address.Service Address | - | 8734 Meadowbrook Lane, Cheyenne, WY 82001 | 8734 Meadowbrook Lane, Cheyenne, WY 82001 | 0.77 | N/A | 0.114,0.300,0.176,0.029 | 0.114,0.300,0.134,0.010 | ❌ |
| Address.Service address pin code | - | WY 82001 | - | 0.80 | - | 0.192,0.317,0.070,0.010 | - | ❌ |
| BalanceDue Date | - | 09/25/26 | September 25, 2026 | 0.88 | 1.0000 | 0.744,0.172,0.141,0.012 | 0.744,0.172,0.142,0.012 | 🟡 |
| BalanceGreaterCheck | - | - | - | 0.94 | - | 0.677,0.239,0.059,0.012 | - | ❌ |
| Category | - | Electricity | Electricity | 0.66 | 0.9500 | 0.567,0.027,0.156,0.025 | 0.567,0.027,0.156,0.025 | ✅ |
| CountMeterIDs | - | 1 | - | 0.77 | - | 0.156,0.466,0.074,0.010 | - | ❌ |
| Current Balance | - | 94.3 | 94.30 | 0.95 | 1.0000 | 0.677,0.292,0.051,0.012 | 0.677,0.292,0.051,0.012 | ✅ |
| End Date | - | 08/31/26 | August 31, 2026 | 0.89 | 1.0000 | 0.758,0.148,0.112,0.012 | 0.758,0.148,0.112,0.012 | ✅ |
| Is_NumMeterIDsListed | - | - | - | 0.95 | - | 0.156,0.466,0.074,0.010 | - | ❌ |
| Is_PrevGreaterThanCurr | - | - | - | 0.94 | - | - | - |  |
| Is_ValidPinCode | - | True | - | 0.93 | - | 0.222,0.317,0.040,0.010 | - | ❌ |
| Is_ValidState | - | True | - | 0.93 | - | 0.114,0.317,0.103,0.012 | - | ❌ |
| Line_Item_Charges.Charge | - | - | 78.20, 45.00, 33.20, 5.00, 3.10 | - | N/A | - | 0.788,0.810,0.041,0.012 | ❌ |
| Line_Item_Charges.Line item Description | - | - | Energy Consumption (920 kWh at $0.085/kWh), Delivery/Distribution Charge, Supply/Generation Charge, Wyoming Energy Surcharge, Taxes & Fees | - | N/A | - | 0.115,0.715,0.242,0.013 | ❌ |
| Meter Number | - | - | Meter #02348719 | - | 1.0000 | - | 0.114,0.466,0.115,0.009 | ❌ |
| MeterRead.Current value | - | - | 920kWh | - | 1.0000 | - | 0.471,0.485,0.059,0.009 | ❌ |
| MeterRead.Delta or Metered value | - | - | -20kWh | - | N/A | - | 0.380,0.446,0.032,0.010 | ❌ |
| MeterRead.Meter ID | - | - | Meter #02348719 | - | 1.0000 | - | 0.114,0.466,0.115,0.009 | ❌ |
| MeterRead.Previous value | - | - | 940kWh | - | 1.0000 | - | 0.779,0.480,0.059,0.009 | ❌ |
| MeterRead.Usage Unit | - | - | kWh | - | 1.0000 | - | 0.380,0.446,0.032,0.010 | ❌ |
| Previous Balance | - | 112.45 | 112.45 | 0.91 | 1.0000 | 0.677,0.239,0.059,0.012 | 0.677,0.239,0.059,0.012 | ✅ |
| Provider | - | Cedar Grove Energy | Cedar Grove Energy | 0.95 | 0.9500 | 0.217,0.027,0.198,0.021 | 0.217,0.027,0.198,0.021 | ✅ |
| StartDate | - | 08/01/26 | August 1, 2026 | 0.91 | 0.9700 | 0.758,0.132,0.104,0.012 | 0.758,0.132,0.105,0.012 | 🟡 |
| Total Balance Due | - | 94.3 | 94.30 | 0.93 | 1.0000 | 0.677,0.323,0.057,0.013 | 0.677,0.292,0.051,0.012 | ❌ |
| Usage.power factor | - | - | $0.085 | - | 1.0000 | - | 0.114,0.548,0.046,0.011 | ❌ |
| Usage.usage | - | - | 920 kWh | - | 1.0000 | - | 0.471,0.485,0.059,0.009 | ❌ |
| UsageMult | - | - | - | 0.93 | - | - | - |  |


## synthetic-expense-utility-electric-bill-scan.jpg

**Durations**

- bda: 23.54s extraction
- llm: 17.358s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| Account Number | - | - | 1234 5678 9012 | - | 0.9600 | - | 0.782,0.086,0.107,0.009 | ❌ |
| Address.Service Address | - | 4912 W Willow Ridge Dr West Jordan, UT 84081 | 4912 W Willow Ridge Dr
West Jordan, UT 84081 | 0.81 | N/A | 0.071,0.202,0.176,0.024 | 0.659,0.177,0.152,0.010 | ❌ |
| Address.Service address pin code | - | UT 84081 | - | 0.86 | - | 0.197,0.216,0.044,0.009 | - | ❌ |
| BalanceDue Date | - | 09/17/26 | Sep 17, 2026 | 0.86 | 0.9900 | 0.782,0.119,0.087,0.011 | 0.782,0.119,0.087,0.011 | ✅ |
| BalanceGreaterCheck | - | - | - | 0.93 | - | 0.879,0.263,0.052,0.010 | - | ❌ |
| Category | - | ELECTRICITY | Electricity | 0.11 | 1.0000 | 0.658,0.031,0.219,0.014 | 0.658,0.031,0.219,0.014 | ✅ |
| CountMeterIDs | - | 1 | - | 0.76 | - | 0.659,0.245,0.103,0.009 | - | ❌ |
| Current Balance | - | 118.63 | 118.63 | 0.95 | 1.0000 | 0.870,0.308,0.061,0.011 | 0.870,0.308,0.061,0.011 | ✅ |
| End Date | - | 08/26/26 | Aug 26, 2026 | 0.86 | 0.9700 | 0.439,0.405,0.047,0.010 | 0.703,0.227,0.131,0.010 | ❌ |
| Is_NumMeterIDsListed | - | - | - | 0.86 | - | 0.659,0.245,0.103,0.009 | - | ❌ |
| Is_PrevGreaterThanCurr | - | - | - | 0.93 | - | 0.659,0.405,0.042,0.010 | - | ❌ |
| Is_ValidPinCode | - | True | - | 0.90 | - | 0.197,0.216,0.044,0.009 | - | ❌ |
| Is_ValidState | - | True | - | 0.90 | - | 0.112,0.216,0.080,0.011 | - | ❌ |
| Line_Item_Charges.Charge | - | - | 65.52, 47.49, 5.50, 0.96, 4.18, 2.98 | - | N/A | - | 0.565,0.718,0.035,0.009 | ❌ |
| Line_Item_Charges.Line item Description | - | - | Supply (Generation) Charge, Delivery (Distribution) Charge, Customer Charge, Utah Clean Energy Program, State Sales Tax, Municipal Franchise Fee | - | N/A | - | 0.060,0.688,0.111,0.010 | ❌ |
| Meter Number | - | - | CGEM12345678 | - | 1.0000 | - | 0.658,0.245,0.103,0.009 | ❌ |
| MeterRead.Current value | - | - | 36885 | - | 1.0000 | - | 0.768,0.405,0.042,0.009 | ❌ |
| MeterRead.Delta or Metered value | - | - | 640 | - | 1.0000 | - | 0.913,0.404,0.024,0.008 | ❌ |
| MeterRead.Meter ID | - | - | CGEM12345678 | - | 1.0000 | - | 0.658,0.245,0.103,0.009 | ❌ |
| MeterRead.Previous value | - | - | 36245 | - | 1.0000 | - | 0.659,0.405,0.042,0.009 | ❌ |
| MeterRead.Usage Unit | - | - | kWh | - | 0.9200 | - | 0.063,0.492,0.011,0.017 | ❌ |
| Previous Balance | - | 112.74 | 112.74 | 0.88 | 1.0000 | 0.879,0.263,0.052,0.010 | 0.878,0.263,0.052,0.010 | 🟡 |
| Provider | - | Cedar Grove Energy | Cedar Grove Energy | 0.94 | 1.0000 | 0.165,0.040,0.303,0.023 | 0.165,0.040,0.303,0.023 | ✅ |
| StartDate | - | 07/28/26 | Jul 28, 2026 | 0.88 | 0.9700 | 0.658,0.228,0.077,0.010 | 0.658,0.227,0.176,0.008 | ❌ |
| Total Balance Due | - | 118.63 | 118.63 | 0.93 | 1.0000 | 0.846,0.332,0.086,0.015 | 0.870,0.308,0.061,0.011 | ❌ |
| Usage.usage | - | - | 640 kWh | - | 0.9900 | - | 0.310,0.643,0.053,0.008 | ❌ |
| UsageMult | - | - | - | 0.92 | - | - | - |  |


## synthetic-expense-utility-water-sewer-bill-render-spanish.png

**Durations**

- bda: 38.44s extraction
- llm: 4.434s extraction

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
| Line_Items.LineItemDescription | - | - | Cargo base de agua, Uso de agua, Cargo base de alcantarillado, Cargo de alcantarillado, Tarifa de aguas pluviales, Impuesto local sobre servicios públicos | - | N/A | - | 0.051,0.463,0.212,0.010 | ❌ |
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


## synthetic-expense-utility-water-sewer-bill-render.pdf

**Durations**

- bda: 25.45s extraction
- llm: 4.134s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| Account_Info.Acct_Name | - | Jordan Rivera | Jordan Rivera | 0.92 | 1.0000 | 0.108,0.319,0.092,0.010 | 0.108,0.319,0.092,0.010 | ✅ |
| Account_Info.Acct_No | - | ****-6732 | ****-6732 | 0.44 | 1.0000 | 0.233,0.155,0.065,0.010 | 0.232,0.156,0.065,0.010 | 🟡 |
| Account_Info.Meter_Number | - | 4872915 | 4872915 | 0.95 | 1.0000 | 0.232,0.177,0.058,0.010 | 0.232,0.177,0.058,0.010 | ✅ |
| Curr_Meter_Reading | - | - | 4,580 gallons | 0.19 | 1.0000 | - | 0.758,0.381,0.090,0.012 | ❌ |
| Dates.Bill_From_Date | - | 08/01/2026 | 08/01/2026 | 0.85 | 1.0000 | 0.233,0.198,0.078,0.010 | 0.233,0.198,0.078,0.010 | ✅ |
| Dates.Bill_To_Date | - | 08/31/2026 | 08/31/2026 | 0.84 | 1.0000 | 0.333,0.198,0.078,0.010 | 0.333,0.198,0.079,0.010 | 🟡 |
| Dates.Billing_Date | - | 09/05/2026 | 09/05/2026 | 0.82 | 1.0000 | 0.233,0.219,0.078,0.010 | 0.233,0.219,0.078,0.010 | ✅ |
| Dates.Due_Date | - | 09/25/2026 | 09/25/2026 | 0.81 | 1.0000 | 0.233,0.240,0.078,0.011 | 0.233,0.240,0.078,0.011 | ✅ |
| Line_Items.Amount or Value | - | - | $25.48 | - | 1.0000 | - | 0.782,0.548,0.045,0.011 | ❌ |
| Line_Items.LineItemDescription | - | - | Water Usage | - | 1.0000 | - | 0.386,0.528,0.085,0.012 | ❌ |
| Prev_Bal | - | 62.48 | 62.48 | 0.94 | 1.0000 | 0.715,0.178,0.046,0.012 | 0.715,0.178,0.046,0.012 | ✅ |
| Prev_Meter_Reading | - | - | 4,900 gallons | 0.92 | 1.0000 | - | 0.773,0.414,0.090,0.012 | ❌ |
| Provider Name | - | Harbor County Water Service | Harbor County Water Service | 0.92 | 1.0000 | 0.104,0.024,0.407,0.024 | 0.104,0.024,0.406,0.024 | 🟡 |
| Service_Address.Building_Line 1 | - | - | 1128 Willow Creek Drive | 0.14 | 1.0000 | - | 0.109,0.386,0.160,0.010 | ❌ |
| Service_Address.City | - | Sedona | Sedona | 0.92 | N/A | 0.108,0.404,0.053,0.011 | - | ❌ |
| Service_Address.State | - | AZ | AZ | 0.91 | 1.0000 | 0.166,0.404,0.019,0.010 | 0.166,0.404,0.019,0.010 | ✅ |
| Service_Address.Street | - | 1128 Willow Creek Drive | 1128 Willow Creek Drive | 0.94 | 1.0000 | 0.145,0.386,0.124,0.010 | 0.109,0.386,0.160,0.010 | ❌ |
| Service_Address.Zip_Code | - | 86336 | 86336 | 0.91 | 1.0000 | 0.189,0.404,0.041,0.009 | 0.189,0.404,0.042,0.009 | 🟡 |
| Tot_Amt | - | 48.76 | 48.76 | 0.93 | 1.0000 | 0.715,0.264,0.046,0.012 | 0.715,0.264,0.046,0.012 | ✅ |
| Total_Current_Charges | - | 48.76 | 48.76 | 0.93 | 1.0000 | 0.715,0.264,0.046,0.012 | 0.715,0.264,0.046,0.012 | ✅ |
| is_total_amount_greater_than_equal_to_current_charges | - | True | Yes | 0.92 | 1.0000 | 0.715,0.178,0.046,0.012 | 0.463,0.299,0.116,0.011 | ❌ |


## synthetic-expense-utility-water-sewer-bill-scan.jpg

**Durations**

- bda: 22.41s extraction
- llm: 3.854s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| Account_Info.Acct_Name | - | Jordan Rivera | Jordan Rivera | 0.85 | 1.0000 | 0.699,0.174,0.092,0.009 | 0.699,0.174,0.092,0.009 | ✅ |
| Account_Info.Acct_No | - | XXXX-XXXX-7821 | XXXX-XXXX-7821 | 0.71 | 1.0000 | 0.698,0.257,0.119,0.009 | 0.698,0.257,0.118,0.009 | 🟡 |
| Account_Info.Meter_Number | - | MTR-1845726 | MTR-1845726 | 0.91 | 1.0000 | 0.699,0.275,0.095,0.010 | 0.699,0.275,0.096,0.009 | 🟡 |
| Curr_Meter_Reading | - | 26,730 | 26,730 | 0.64 | 1.0000 | 0.326,0.413,0.042,0.010 | 0.326,0.413,0.041,0.010 | 🟡 |
| Dates.Bill_From_Date | - | 07/24/2026 | Jul 24, 2026 | 0.67 | 0.9800 | 0.191,0.344,0.082,0.010 | 0.191,0.344,0.183,0.009 | ❌ |
| Dates.Bill_To_Date | - | 08/24/2026 | Aug 24, 2026 | 0.65 | 0.9800 | 0.288,0.345,0.086,0.010 | 0.242,0.344,0.132,0.009 | ❌ |
| Dates.Billing_Date | - | 08/25/2026 | Aug 25, 2026 | 0.71 | 1.0000 | 0.824,0.074,0.095,0.012 | 0.824,0.074,0.095,0.012 | ✅ |
| Dates.Due_Date | - | 09/15/2026 | Sep 15, 2026 | 0.72 | 1.0000 | 0.824,0.090,0.095,0.012 | 0.824,0.090,0.095,0.012 | ✅ |
| Line_Items.Amount or Value | - | - | $14.45 | - | 1.0000 | - | 0.560,0.539,0.042,0.010 | ❌ |
| Line_Items.LineItemDescription | - | - | Water Service Charge | - | 1.0000 | - | 0.078,0.537,0.131,0.011 | ❌ |
| Prev_Bal | - | 48.73 | 48.73 | 0.91 | 1.0000 | 0.431,0.173,0.045,0.011 | 0.431,0.173,0.045,0.011 | ✅ |
| Prev_Meter_Reading | - | 23,010 | 23,010 | 0.73 | 1.0000 | 0.326,0.431,0.042,0.010 | 0.326,0.431,0.041,0.010 | 🟡 |
| Provider Name | - | Harbor County Water Service | Harbor County Water Service | 0.89 | 1.0000 | 0.196,0.036,0.354,0.020 | 0.196,0.036,0.354,0.020 | ✅ |
| Service_Address.Building_Line 1 | - | 4824 Aspen Ridge Dr | 4824 Aspen Ridge Dr | 0.80 | 1.0000 | 0.699,0.192,0.144,0.012 | 0.699,0.192,0.144,0.012 | ✅ |
| Service_Address.City | - | Loveland | Loveland | 0.84 | N/A | 0.699,0.206,0.065,0.011 | - | ❌ |
| Service_Address.State | - | CO | CO | 0.89 | 0.9900 | 0.769,0.207,0.020,0.009 | 0.286,0.099,0.021,0.010 | ❌ |
| Service_Address.Street | - | 4824 Aspen Ridge Dr | 4824 Aspen Ridge Dr | 0.88 | 1.0000 | 0.737,0.192,0.106,0.011 | 0.699,0.192,0.144,0.012 | ❌ |
| Service_Address.Zip_Code | - | 80538 | 80538 | 0.90 | 0.9800 | 0.793,0.207,0.042,0.009 | 0.793,0.207,0.042,0.009 | ✅ |
| Tot_Amt | - | 64.86 | 64.86 | 0.90 | 1.0000 | 0.400,0.285,0.067,0.016 | 0.430,0.244,0.046,0.011 | ❌ |
| Total_Current_Charges | - | 64.86 | 64.86 | 0.91 | 1.0000 | 0.430,0.244,0.046,0.011 | 0.430,0.244,0.046,0.011 | ✅ |
| is_total_amount_greater_than_equal_to_current_charges | - | True | Yes | 0.89 | 1.0000 | 0.430,0.244,0.046,0.011 | 0.556,0.868,0.077,0.011 | ❌ |


## synthetic-insurance-health-insurance-premium-render-spanish.png

**Durations**

- bda: 30.71s extraction
- llm: 2.046s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| coverage_end_date | - | 2026-08-31 | 2026-08-31 | 0.69 | 0.9900 | 0.436,0.278,0.035,0.010 | 0.350,0.242,0.195,0.010 | ❌ |
| coverage_start_date | - | 2026-08-01 | 2026-08-01 | 0.75 | 0.9900 | 0.487,0.265,0.051,0.009 | 0.337,0.242,0.209,0.010 | ❌ |
| employer_name | - | - | - | 0.91 | N/A | - | - |  |
| insurer_or_marketplace_name | - | Harbor Health Plan | Harbor Health Plan, Inc. | 0.25 | 1.0000 | 0.127,0.036,0.201,0.044 | 0.433,0.035,0.107,0.010 | ❌ |
| payment_due_date | - | 2026-08-25 | 2026-08-25 | 0.10 | 1.0000 | 0.387,0.327,0.126,0.012 | 0.336,0.327,0.176,0.012 | ❌ |
| payment_frequency | - | mensual | monthly | 0.62 | 0.9900 | 0.709,0.251,0.055,0.008 | 0.631,0.251,0.133,0.008 | ❌ |
| payment_status | - | Paid | Paid | 0.72 | 1.0000 | - | 0.630,0.390,0.095,0.010 | ❌ |
| policy_or_member_id | - | MEM-87X4-3K2L | MEM-87X4-3K2L | 0.89 | 0.9900 | 0.731,0.127,0.132,0.009 | 0.731,0.127,0.132,0.009 | ✅ |
| policyholder_name | - | María Elena Salazar | María Elena Salazar | 0.78 | 0.9900 | 0.049,0.242,0.166,0.011 | 0.049,0.242,0.165,0.010 | 🟡 |
| premium_amount | - | 260 | 450.00 | 0.89 | 1.0000 | 0.866,0.334,0.065,0.011 | 0.877,0.251,0.055,0.010 | ❌ |
| statement_date | - | 2026-09-02 | 2026-09-02 | 0.77 | 0.9900 | 0.731,0.050,0.186,0.012 | 0.731,0.050,0.186,0.011 | 🟡 |
| subsidy_or_tax_credit_amount | - | 225 | -225.00 | 0.81 | 1.0000 | 0.873,0.278,0.059,0.010 | 0.873,0.278,0.059,0.010 | ✅ |


## synthetic-insurance-health-insurance-premium-render.pdf

**Durations**

- bda: 24.28s extraction
- llm: 1.952s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| coverage_end_date | - | 2026-08-31 | 2026-08-31 | 0.84 | 1.0000 | 0.698,0.246,0.115,0.013 | 0.697,0.246,0.115,0.013 | 🟡 |
| coverage_start_date | - | 2026-08-01 | 2026-08-01 | 0.84 | 0.9300 | 0.698,0.229,0.106,0.013 | 0.697,0.229,0.107,0.013 | 🟡 |
| employer_name | - | - | - | 0.94 | N/A | - | - |  |
| insurer_or_marketplace_name | - | Clearview Insurance Services | Clearview Insurance Services | 0.89 | 1.0000 | 0.128,0.058,0.309,0.031 | 0.110,0.184,0.218,0.011 | ❌ |
| payment_due_date | - | 2026-09-20 | 2026-09-20 | 0.93 | 1.0000 | 0.698,0.277,0.084,0.010 | 0.698,0.277,0.083,0.010 | 🟡 |
| payment_frequency | - | Monthly | Monthly | 0.88 | 1.0000 | 0.788,0.513,0.057,0.013 | 0.789,0.513,0.057,0.013 | 🟡 |
| payment_status | - | Paid | Paid | 0.81 | N/A | - | 0.128,0.823,0.155,0.013 | ❌ |
| policy_or_member_id | - | CLV-98274651 | CLV-98274651 | 0.94 | 1.0000 | 0.250,0.451,0.103,0.011 | 0.250,0.451,0.103,0.011 | ✅ |
| policyholder_name | - | Jordan Rivera | Jordan Rivera | 0.93 | 1.0000 | 0.249,0.366,0.098,0.010 | 0.249,0.366,0.097,0.010 | 🟡 |
| premium_amount | - | 390 | 600.00 | 0.95 | 1.0000 | 0.782,0.474,0.064,0.013 | 0.787,0.386,0.058,0.012 | ❌ |
| statement_date | - | 2026-09-05 | 2026-09-05 | 0.92 | 1.0000 | 0.698,0.197,0.084,0.011 | 0.697,0.198,0.084,0.010 | 🟡 |
| subsidy_or_tax_credit_amount | - | 240 | -240.00 | 0.82 | 1.0000 | 0.783,0.414,0.063,0.012 | 0.783,0.415,0.063,0.012 | 🟡 |


## synthetic-insurance-health-insurance-premium-scan.jpg

**Durations**

- bda: 19.48s extraction
- llm: 2.211s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| coverage_end_date | - | 2026-09-30 | 09/30/2026 | 0.91 | 0.8500 | 0.890,0.087,0.081,0.012 | 0.890,0.087,0.081,0.012 | ✅ |
| coverage_start_date | - | 2026-09-01 | 09/01/2026 | 0.82 | 1.0000 | - | 0.791,0.068,0.081,0.011 | ❌ |
| employer_name | - | - | - | 0.94 | - | - | - |  |
| insurer_or_marketplace_name | - | Harbor Health Plan | Harbor Health Plan, Inc. | 0.70 | 1.0000 | 0.135,0.042,0.185,0.045 | 0.352,0.039,0.111,0.012 | ❌ |
| payment_due_date | - | 2026-09-15 | 09/15/2026 | 0.92 | 1.0000 | 0.789,0.103,0.081,0.011 | 0.789,0.103,0.082,0.011 | 🟡 |
| payment_frequency | - | monthly | monthly | 0.86 | 1.0000 | 0.080,0.564,0.055,0.012 | 0.047,0.564,0.325,0.014 | ❌ |
| payment_status | - | Paid | Paid | 0.88 | 1.0000 | 0.729,0.162,0.057,0.015 | 0.729,0.162,0.159,0.016 | ❌ |
| policy_or_member_id | - | HHP123456789 | HHP123456789 | 0.95 | 1.0000 | 0.273,0.321,0.102,0.010 | 0.273,0.322,0.101,0.010 | 🟡 |
| policyholder_name | - | Jordan Rivera | Jordan Rivera | 0.94 | 1.0000 | 0.094,0.192,0.103,0.011 | 0.094,0.192,0.104,0.012 | 🟡 |
| premium_amount | - | 636.25 | 636.25 | 0.95 | 1.0000 | 0.884,0.319,0.062,0.013 | 0.884,0.319,0.062,0.013 | ✅ |
| statement_date | - | 2026-09-01 | 09/01/2026 | 0.91 | 1.0000 | 0.791,0.068,0.081,0.011 | 0.791,0.068,0.081,0.011 | ✅ |
| subsidy_or_tax_credit_amount | - | 323.75 | -323.75 | 0.95 | 1.0000 | 0.884,0.269,0.064,0.013 | 0.883,0.269,0.064,0.012 | 🟡 |


## synthetic-investment-and-royalty-income-render-spanish.png

**Durations**

- bda: 20.3s extraction
- llm: 2.154s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_balance | - | - | $51,000.00 | - | 1.0000 | - | 0.857,0.423,0.082,0.011 | ❌ |
| account_holder_name | - | María Elena Vásquez | María Elena Vásquez | 0.79 | 0.9400 | 0.057,0.205,0.167,0.012 | 0.057,0.205,0.167,0.012 | ✅ |
| account_number | - | - | ***-***-6721 | - | 0.7600 | - | 0.710,0.191,0.084,0.009 | ❌ |
| account_type | - | - | IRA Tradicional | - | 1.0000 | - | 0.724,0.027,0.178,0.013 | ❌ |
| capital_gains_distributions_cumulative | - | - | - | 0.78 | - | - | - |  |
| contribution_dates | - | - | 03/10/2025, 06/15/2025 | - | N/A | - | 0.057,0.562,0.072,0.008 | ❌ |
| distribution_dates | - | - | 11/20/2025 | - | 1.0000 | - | 0.058,0.600,0.071,0.008 | ❌ |
| dividend_payments_cumulative | - | - | - | 0.92 | - | - | - |  |
| document_type | - | Brokerage Statement | - | 0.75 | - | 0.097,0.088,0.070,0.010 | - | ❌ |
| financial_institution | - | Harbor Brokerage Services | Harbor Brokerage Services, LLC | 0.57 | 1.0000 | 0.112,0.028,0.315,0.016 | 0.045,0.088,0.222,0.010 | ❌ |
| interest_credits_cumulative | - | - | - | 0.91 | - | - | - |  |
| statement_period_end | - | 2025-12-31 | - | 0.86 | - | 0.865,0.079,0.088,0.009 | - | ❌ |
| statement_period_start | - | 2025-01-01 | - | 0.80 | - | 0.754,0.079,0.088,0.009 | - | ❌ |
| tax_year | - | - | 2025 | - | N/A | - | - |  |
| total_value | - | 51000 | - | 0.91 | - | 0.856,0.423,0.083,0.011 | - | ❌ |


## synthetic-investment-and-royalty-income-render.pdf

**Durations**

- bda: 20.59s extraction
- llm: 1.49s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_balance | - | - | $49,000.00 | - | 1.0000 | - | 0.779,0.684,0.087,0.014 | ❌ |
| account_holder_name | - | Jordan Rivera | Jordan Rivera | 0.91 | 1.0000 | 0.117,0.254,0.112,0.012 | 0.117,0.254,0.113,0.012 | 🟡 |
| account_number | - | - | xxxx-xxxx-1392 | - | 0.9100 | - | 0.679,0.260,0.117,0.011 | ❌ |
| account_type | - | - | Traditional IRA | - | 1.0000 | - | 0.678,0.229,0.112,0.011 | ❌ |
| capital_gains_distributions_cumulative | - | - | - | 0.91 | - | - | - |  |
| contribution_dates | - | - | 01/01/2025 - 12/31/2025 | - | N/A | - | 0.290,0.171,0.006,0.002 | ❌ |
| distribution_dates | - | - | 01/01/2025 - 12/31/2025 | - | N/A | - | 0.290,0.171,0.006,0.002 | ❌ |
| dividend_payments_cumulative | - | - | - | 0.92 | - | - | - |  |
| document_type | - | - | - | 0.06 | - | - | - |  |
| financial_institution | - | Seaport Financial Group | Seaport Financial Group | 0.88 | 0.9800 | 0.224,0.054,0.191,0.054 | 0.114,0.166,0.173,0.013 | ❌ |
| interest_credits_cumulative | - | - | - | 0.91 | - | - | - |  |
| statement_period_end | - | 2025-12-31 | - | 0.84 | - | 0.781,0.309,0.087,0.014 | - | ❌ |
| statement_period_start | - | 2025-01-01 | - | 0.80 | - | 0.679,0.308,0.098,0.014 | - | ❌ |
| tax_year | - | - | 2025 | - | 1.0000 | - | 0.748,0.290,0.038,0.011 | ❌ |
| total_value | - | 49000 | - | 0.93 | - | 0.778,0.683,0.088,0.014 | - | ❌ |


## synthetic-investment-and-royalty-income-scan.jpg

**Durations**

- bda: 20.28s extraction
- llm: 1.745s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| account_balance | - | - | $46,000.00 | - | 1.0000 | - | 0.726,0.299,0.147,0.020 | ❌ |
| account_holder_name | - | Alexis Morgan | Alexis Morgan | 0.93 | 1.0000 | 0.053,0.145,0.101,0.011 | 0.053,0.145,0.101,0.011 | ✅ |
| account_number | - | - | IRA-7821-****-5542 | - | 0.9000 | - | 0.665,0.148,0.135,0.009 | ❌ |
| account_type | - | - | Traditional IRA | - | 1.0000 | - | 0.665,0.165,0.101,0.009 | ❌ |
| capital_gains_distributions_cumulative | - | - | - | 0.89 | - | - | - |  |
| contribution_dates | - | - | 02/14/2026, 05/12/2026 | - | N/A | - | 0.059,0.590,0.074,0.009 | ❌ |
| distribution_dates | - | - | 07/20/2026 | - | 1.0000 | - | 0.059,0.629,0.075,0.009 | ❌ |
| dividend_payments_cumulative | - | - | - | 0.90 | - | - | - |  |
| document_type | - | IRA ACCOUNT STATEMENT | - | 0.38 | - | 0.750,0.050,0.212,0.010 | - | ❌ |
| financial_institution | - | Harbor Brokerage Services | Harbor Brokerage Services, Inc. | 0.65 | 1.0000 | 0.135,0.044,0.345,0.020 | 0.666,0.182,0.121,0.011 | ❌ |
| interest_credits_cumulative | - | - | - | 0.90 | - | - | - |  |
| statement_period_end | - | 2026-08-31 | - | 0.83 | - | 0.793,0.131,0.113,0.011 | - | ❌ |
| statement_period_start | - | 2026-01-01 | - | 0.87 | - | 0.665,0.131,0.111,0.011 | - | ❌ |
| tax_year | - | - | 2026 | - | 1.0000 | - | 0.743,0.114,0.033,0.009 | ❌ |
| total_value | - | 46000 | - | 0.93 | - | 0.726,0.299,0.147,0.020 | - | ❌ |


## synthetic-public-benefits-identity-proof-state-photo-id.jpg

**Durations**

- llm: 2.289s extraction
- textract: 2.56s extraction

| Field | Expected | TEXTRACT Value | LLM (via Textract) Value | TEXTRACT Conf | LLM Conf | TEXTRACT Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| ADDRESS_DETAILS.CITY | LAS VEGAS | ✅ LAS VEGAS | ✅ LAS VEGAS | 0.97 | N/A | - | 0.405,0.501,0.096,0.027 | ❌ |
| ADDRESS_DETAILS.STATE | NV | ✅ NV | ✅ NV | 0.98 | 1.0000 | 0.505,0.498,0.024,0.021 | 0.506,0.499,0.023,0.020 | 🟡 |
| ADDRESS_DETAILS.STREET_ADDRESS | 4821 DESERT BLOOM AVE | ✅ 4821 DESERT BLOOM AVE | ✅ 4821 DESERT BLOOM AVE | 0.97 | 1.0000 | 0.402,0.458,0.209,0.041 | 0.403,0.461,0.208,0.038 | 🟡 |
| ADDRESS_DETAILS.ZIP_CODE | 89146 | ✅ 89146 | ✅ 89146 | 0.98 | 1.0000 | 0.646,0.588,0.057,0.028 | 0.534,0.494,0.049,0.023 | ❌ |
| CLASS | D | ✅ D | ✅ D | 0.98 | 0.9700 | 0.353,0.730,0.012,0.020 | 0.355,0.731,0.011,0.019 | 🟡 |
| COUNTY | - | - | - | 0.99 | - | - | - |  |
| DATE_OF_BIRTH | 1996-05-14 | ✅ 1996-05-14 | ✅ 1996-05-14 | 0.96 | 1.0000 | 0.638,0.460,0.105,0.034 | 0.639,0.462,0.104,0.032 | 🟡 |
| DATE_OF_ISSUE | 2021-06-18 | ✅ 2021-06-18 | ✅ 2021-06-18 | 0.98 | 1.0000 | 0.409,0.606,0.090,0.031 | 0.410,0.608,0.089,0.030 | 🟡 |
| ENDORSEMENTS | - | - | - | 0.98 | - | - | - |  |
| EXPIRATION_DATE | 2029-06-18 | ✅ 2029-06-18 | ✅ 2029-06-18 | 0.97 | 1.0000 | 0.536,0.594,0.091,0.031 | 0.537,0.596,0.090,0.030 | 🟡 |
| ID_NUMBER | DEMO-4821-55 | ❌ DEMO482155 | ✅ DEMO-4821-55 | 0.96 | 0.9800 | 0.633,0.360,0.144,0.038 | 0.635,0.362,0.142,0.034 | 🟡 |
| NAME_DETAILS.FIRST_NAME | ELENA | ✅ ELENA | ✅ ELENA | 0.94 | 1.0000 | 0.398,0.378,0.070,0.030 | 0.399,0.380,0.069,0.028 | 🟡 |
| NAME_DETAILS.LAST_NAME | MARTINEZ | ✅ MARTINEZ | ✅ MARTINEZ | 0.62 | 1.0000 | 0.471,0.369,0.108,0.034 | 0.473,0.370,0.107,0.031 | 🟡 |
| NAME_DETAILS.MIDDLE_NAME | - | ❌ MARTINEZ | - | 0.98 | - | 0.471,0.369,0.108,0.034 | - | ❌ |
| NAME_DETAILS.SUFFIX | - | - | - | 0.99 | - | - | - |  |
| PERSONAL_DETAILS.EYE_COLOR | - | - | - | - | - | - | - |  |
| PERSONAL_DETAILS.HAIR_COLOR | - | - | - | - | - | - | - |  |
| PERSONAL_DETAILS.HEIGHT | - | - | - | - | - | - | - |  |
| PERSONAL_DETAILS.SEX | F | ✅ F | ✅ F | 1.00 | 1.0000 | 0.761,0.458,0.014,0.024 | 0.763,0.460,0.013,0.022 | 🟡 |
| PERSONAL_DETAILS.WEIGHT | - | - | - | - | - | - | - |  |
| RESTRICTIONS | NONE | ✅ NONE | ✅ NONE | 0.98 | 1.0000 | 0.431,0.718,0.046,0.025 | 0.433,0.721,0.045,0.022 | 🟡 |
| STATE_NAME | - | - | - | 0.13 | - | - | - |  |


## synthetic-public-benefits-income-proof-pay-statement-photo.png

**Durations**

- bda: 23.66s extraction
- llm: 11.64s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| CityTaxes.ItemDescription | - | - | - | - | N/A | - | - |  |
| CityTaxes.Period | - | - | - | - | N/A | - | - |  |
| CityTaxes.YTD | - | - | - | - | N/A | - | - |  |
| CompanyAddress.City | - | Baltimore | Baltimore | 0.93 | N/A | 0.164,0.132,0.066,0.013 | - | ❌ |
| CompanyAddress.Line1 | - | 2458 Harford Rd | 2458 Harford Rd | 0.95 | 1.0000 | 0.163,0.114,0.108,0.013 | 0.163,0.114,0.108,0.012 | 🟡 |
| CompanyAddress.Line2 | - | - | - | 0.94 | N/A | - | - |  |
| CompanyAddress.State | - | MD | MD | 0.93 | 1.0000 | 0.236,0.134,0.023,0.011 | 0.236,0.133,0.023,0.011 | 🟡 |
| CompanyAddress.ZipCode | - | 21218 | 21218 | 0.93 | 1.0000 | 0.263,0.134,0.040,0.011 | 0.263,0.134,0.040,0.011 | ✅ |
| CurrentGrossPay | - | 1505.66 | 1505.66 | 0.93 | 1.0000 | 0.674,0.493,0.063,0.012 | 0.674,0.493,0.063,0.012 | ✅ |
| CurrentNetPay | - | 1148.22 | 1148.22 | 0.91 | 1.0000 | 0.384,0.764,0.093,0.020 | 0.384,0.764,0.093,0.019 | 🟡 |
| CurrentTotalDeductions | - | 457.44 | 457.44 | 0.95 | 1.0000 | 0.493,0.713,0.052,0.014 | 0.494,0.713,0.052,0.014 | 🟡 |
| EmployeeAddress.City | - | Baltimore | Baltimore | 0.94 | N/A | 0.292,0.238,0.057,0.012 | - | ❌ |
| EmployeeAddress.Line1 | - | 1824 E Lafayette Ave | 1824 E Lafayette Ave | 0.95 | 1.0000 | 0.293,0.219,0.118,0.013 | 0.293,0.220,0.118,0.013 | 🟡 |
| EmployeeAddress.Line2 | - | - | - | 0.93 | N/A | - | - |  |
| EmployeeAddress.State | - | MD | MD | 0.94 | 1.0000 | 0.354,0.238,0.020,0.010 | 0.236,0.133,0.023,0.011 | ❌ |
| EmployeeAddress.ZipCode | - | 21213 | 21213 | 0.94 | 1.0000 | 0.379,0.238,0.035,0.010 | 0.379,0.238,0.035,0.010 | ✅ |
| EmployeeName.FirstName | - | Jasmine | Jasmine | 0.93 | 1.0000 | 0.292,0.202,0.046,0.010 | 0.292,0.201,0.046,0.010 | 🟡 |
| EmployeeName.LastName | - | Carter | Carter | 0.91 | 1.0000 | 0.341,0.202,0.035,0.010 | 0.341,0.202,0.035,0.010 | ✅ |
| EmployeeName.MiddleName | - | - | - | 0.93 | N/A | - | - |  |
| EmployeeName.SuffixName | - | - | - | 0.93 | N/A | - | - |  |
| EmployeeNumber | - | 10482 | 10482 | 0.94 | 1.0000 | 0.292,0.261,0.035,0.010 | 0.292,0.261,0.035,0.010 | ✅ |
| FederalFilingStatus | - | Married | Married | 0.72 | 1.0000 | 0.799,0.579,0.045,0.010 | 0.799,0.579,0.044,0.010 | 🟡 |
| FederalTaxes.ItemDescription | - | - | Federal Income Tax | - | 1.0000 | - | 0.143,0.584,0.116,0.011 | ❌ |
| FederalTaxes.Period | - | - | 186.11 | - | 1.0000 | - | 0.495,0.581,0.046,0.012 | ❌ |
| FederalTaxes.YTD | - | - | 2287.59 | - | 1.0000 | - | 0.637,0.580,0.060,0.012 | ❌ |
| HolidayHourlyRate | - | - | - | 0.95 | N/A | - | - |  |
| PayDate | - | 2026-04-17 | 04/17/2026 | 0.66 | 1.0000 | 0.704,0.140,0.072,0.013 | 0.704,0.140,0.072,0.013 | ✅ |
| PayPeriodEndDate | - | 2026-04-15 | 04/15/2026 | 0.77 | 1.0000 | 0.796,0.122,0.070,0.012 | 0.796,0.122,0.070,0.012 | ✅ |
| PayPeriodStartDate | - | 2026-04-01 | 04/01/2026 | 0.78 | 1.0000 | 0.704,0.121,0.072,0.013 | 0.705,0.121,0.072,0.013 | 🟡 |
| PayrollNumber | - | - | - | 0.95 | N/A | - | - |  |
| RegularHourlyRate | - | 18.25 | 18.25 | 0.94 | 1.0000 | 0.290,0.302,0.039,0.012 | 0.290,0.302,0.039,0.012 | ✅ |
| StateFilingStatus | - | Married | Married | 0.12 | 1.0000 | 0.799,0.579,0.044,0.010 | 0.799,0.579,0.044,0.010 | ✅ |
| StateTaxes.ItemDescription | - | - | Maryland State Tax | - | 1.0000 | - | 0.142,0.610,0.120,0.014 | ❌ |
| StateTaxes.Period | - | - | 72.78 | - | 1.0000 | - | 0.502,0.606,0.041,0.012 | ❌ |
| StateTaxes.YTD | - | - | 883.44 | - | 1.0000 | - | 0.649,0.604,0.049,0.013 | ❌ |
| YTDCityTax | - | - | - | 0.95 | N/A | - | - |  |
| YTDFederalTax | - | 2287.59 | 2287.59 | 0.94 | 1.0000 | 0.636,0.579,0.060,0.013 | 0.637,0.580,0.060,0.012 | 🟡 |
| YTDGrossPay | - | 18511.2 | 18511.20 | 0.96 | 1.0000 | 0.810,0.492,0.071,0.012 | 0.809,0.492,0.071,0.012 | 🟡 |
| YTDNetPay | - | 12921.89 | 12921.89 | 0.93 | 1.0000 | 0.678,0.855,0.078,0.017 | 0.678,0.855,0.078,0.016 | 🟡 |
| YTDStateTax | - | 883.44 | 883.44 | 0.91 | 1.0000 | 0.649,0.604,0.049,0.012 | 0.649,0.604,0.049,0.013 | 🟡 |
| YTDTotalDeductions | - | 5589.31 | 5589.31 | 0.95 | 1.0000 | 0.640,0.711,0.061,0.014 | 0.640,0.712,0.062,0.014 | 🟡 |
| are_field_names_sufficient | - | True | - | 0.46 | N/A | - | - |  |
| currency | - | USD | USD | 0.92 | N/A | 0.236,0.134,0.023,0.011 | - | ❌ |
| is_gross_pay_valid | - | True | - | 0.89 | N/A | 0.269,0.863,0.080,0.016 | - | ❌ |
| is_ytd_gross_pay_highest | - | True | - | 0.90 | N/A | 0.269,0.863,0.080,0.016 | - | ❌ |


## synthetic-public-benefits-income-proof-pay-statement-rendered.png

**Durations**

- bda: 22.66s extraction
- llm: 12.594s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| CityTaxes.ItemDescription | - | - | - | - | N/A | - | - |  |
| CityTaxes.Period | - | - | - | - | N/A | - | - |  |
| CityTaxes.YTD | - | - | - | - | N/A | - | - |  |
| CompanyAddress.City | - | Baltimore | Baltimore | 0.93 | N/A | 0.510,0.134,0.076,0.016 | - | ❌ |
| CompanyAddress.Line1 | - | 2458 Harford Rd | 2458 Harford Rd | 0.94 | 1.0000 | 0.509,0.108,0.129,0.014 | 0.067,0.072,0.125,0.012 | ❌ |
| CompanyAddress.Line2 | - | - | - | 0.92 | N/A | - | - |  |
| CompanyAddress.State | - | MD | MD | 0.93 | 1.0000 | 0.594,0.134,0.027,0.014 | 0.152,0.093,0.027,0.013 | ❌ |
| CompanyAddress.ZipCode | - | 21218 | 21218 | 0.93 | 1.0000 | 0.627,0.134,0.047,0.014 | 0.185,0.093,0.047,0.013 | ❌ |
| CurrentGrossPay | - | 1505.66 | 1505.66 | 0.92 | 1.0000 | 0.682,0.470,0.075,0.016 | 0.673,0.512,0.072,0.014 | ❌ |
| CurrentNetPay | - | 1148.22 | 1148.22 | 0.89 | 1.0000 | 0.335,0.803,0.107,0.022 | 0.341,0.804,0.103,0.018 | ❌ |
| CurrentTotalDeductions | - | 457.44 | 457.44 | 0.95 | 1.0000 | 0.461,0.745,0.060,0.016 | 0.463,0.753,0.058,0.014 | ❌ |
| EmployeeAddress.City | - | Baltimore | Baltimore | 0.93 | N/A | 0.208,0.130,0.072,0.015 | - | ❌ |
| EmployeeAddress.Line1 | - | 1824 E Lafayette Ave | 1824 E Lafayette Ave | 0.94 | 1.0000 | 0.208,0.105,0.152,0.016 | 0.221,0.193,0.146,0.014 | ❌ |
| EmployeeAddress.Line2 | - | - | - | 0.91 | N/A | - | - |  |
| EmployeeAddress.State | - | MD | MD | 0.94 | 1.0000 | 0.287,0.130,0.026,0.013 | 0.152,0.093,0.027,0.013 | ❌ |
| EmployeeAddress.ZipCode | - | 21213 | 21213 | 0.93 | 1.0000 | 0.318,0.129,0.044,0.013 | 0.326,0.215,0.042,0.012 | ❌ |
| EmployeeName.FirstName | - | Jasmine | Jasmine | 0.91 | 1.0000 | 0.207,0.078,0.059,0.013 | 0.219,0.170,0.057,0.011 | ❌ |
| EmployeeName.LastName | - | Carter | Carter | 0.90 | 1.0000 | 0.272,0.078,0.044,0.013 | 0.281,0.170,0.043,0.012 | ❌ |
| EmployeeName.MiddleName | - | - | - | 0.92 | N/A | - | - |  |
| EmployeeName.SuffixName | - | - | - | 0.93 | N/A | - | - |  |
| EmployeeNumber | - | 10482 | 10482 | 0.93 | 1.0000 | 0.208,0.162,0.044,0.013 | 0.220,0.243,0.042,0.012 | ❌ |
| FederalFilingStatus | - | Married | Married | 0.26 | 1.0000 | 0.828,0.583,0.051,0.012 | 0.813,0.611,0.049,0.011 | ❌ |
| FederalTaxes.ItemDescription | - | - | Federal Income Tax | - | 1.0000 | - | 0.069,0.611,0.129,0.012 | ❌ |
| FederalTaxes.Period | - | - | 186.11 | - | 1.0000 | - | 0.465,0.610,0.053,0.013 | ❌ |
| FederalTaxes.YTD | - | - | 2287.59 | - | 1.0000 | - | 0.628,0.610,0.069,0.014 | ❌ |
| HolidayHourlyRate | - | - | - | 0.94 | N/A | - | - |  |
| PayDate | - | - | 04/17/2026 | 0.94 | 1.0000 | - | 0.739,0.094,0.088,0.013 | ❌ |
| PayPeriodEndDate | - | - | 04/15/2026 | 0.94 | 1.0000 | - | 0.852,0.070,0.086,0.013 | ❌ |
| PayPeriodStartDate | - | - | 04/01/2026 | 0.94 | 1.0000 | - | 0.739,0.070,0.087,0.013 | ❌ |
| PayrollNumber | - | - | - | 0.94 | N/A | - | - |  |
| RegularHourlyRate | - | 18.25 | 18.25 | 0.93 | 1.0000 | 0.207,0.217,0.050,0.016 | 0.219,0.291,0.048,0.014 | ❌ |
| StateFilingStatus | - | Married | Married | 0.08 | 1.0000 | 0.828,0.583,0.051,0.012 | 0.813,0.611,0.049,0.011 | ❌ |
| StateTaxes.ItemDescription | - | - | Maryland State Tax | - | 1.0000 | - | 0.069,0.639,0.134,0.014 | ❌ |
| StateTaxes.Period | - | - | 72.78 | - | 1.0000 | - | 0.473,0.638,0.047,0.014 | ❌ |
| StateTaxes.YTD | - | - | 883.44 | - | 1.0000 | - | 0.641,0.638,0.056,0.013 | ❌ |
| YTDCityTax | - | - | - | 0.95 | N/A | - | - |  |
| YTDFederalTax | - | 2287.59 | 2287.59 | 0.93 | 1.0000 | 0.634,0.582,0.073,0.015 | 0.628,0.610,0.069,0.014 | ❌ |
| YTDGrossPay | - | 18511.2 | 18511.20 | 0.96 | 1.0000 | 0.844,0.470,0.083,0.016 | 0.828,0.512,0.081,0.014 | ❌ |
| YTDNetPay | - | 12921.89 | 12921.89 | 0.93 | 1.0000 | 0.670,0.916,0.090,0.017 | 0.662,0.902,0.086,0.015 | ❌ |
| YTDStateTax | - | 883.44 | 883.44 | 0.90 | 1.0000 | 0.648,0.614,0.059,0.015 | 0.641,0.638,0.056,0.013 | ❌ |
| YTDTotalDeductions | - | 5589.31 | 5589.31 | 0.95 | 1.0000 | 0.632,0.745,0.072,0.016 | 0.626,0.753,0.070,0.014 | ❌ |
| are_field_names_sufficient | - | True | - | 0.51 | N/A | - | - |  |
| currency | - | USD | USD | 0.93 | N/A | - | - |  |
| is_gross_pay_valid | - | True | - | 0.89 | N/A | 0.206,0.916,0.089,0.017 | - | ❌ |
| is_ytd_gross_pay_highest | - | True | - | 0.89 | N/A | 0.206,0.916,0.089,0.017 | - | ❌ |


## synthetic-public-benefits-income-proof-pay-stub.jpg

**Durations**

- bda: 25.03s extraction
- llm: 11.318s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| CityTaxes.ItemDescription | - | - | - | - | N/A | - | - |  |
| CityTaxes.Period | - | - | - | - | N/A | - | - |  |
| CityTaxes.YTD | - | - | - | - | N/A | - | - |  |
| CompanyAddress.City | Hartford | ✅ Hartford | ✅ Hartford | 0.94 | N/A | 0.137,0.289,0.042,0.017 | - | ❌ |
| CompanyAddress.Line1 | 1234 Community Way | ✅ 1234 Community Way | ✅ 1234 Community Way | 0.95 | 1.0000 | 0.137,0.261,0.104,0.024 | 0.137,0.261,0.104,0.021 | 🟡 |
| CompanyAddress.Line2 | - | - | - | 0.95 | N/A | - | - |  |
| CompanyAddress.State | ST | ✅ ST | ✅ ST | 0.92 | 1.0000 | 0.182,0.288,0.013,0.012 | 0.182,0.288,0.013,0.012 | ✅ |
| CompanyAddress.ZipCode | 06103 | ✅ 06103 | ✅ 06103 | 0.94 | 1.0000 | 0.197,0.285,0.029,0.014 | 0.197,0.285,0.029,0.014 | ✅ |
| CurrentGrossPay | 1350.00 | 🟡 1350 | ✅ 1350.00 | 0.95 | 1.0000 | 0.407,0.619,0.048,0.020 | 0.400,0.376,0.039,0.016 | ❌ |
| CurrentNetPay | 1037.56 | ✅ 1037.56 | ✅ 1037.56 | 0.94 | 1.0000 | 0.737,0.751,0.041,0.018 | 0.755,0.579,0.047,0.020 | ❌ |
| CurrentTotalDeductions | 312.44 | ✅ 312.44 | ✅ 312.44 | 0.43 | 1.0000 | 0.765,0.533,0.031,0.015 | 0.765,0.532,0.031,0.015 | 🟡 |
| EmployeeAddress.City | - | - | - | 0.93 | N/A | - | - |  |
| EmployeeAddress.Line1 | - | - | - | 0.94 | N/A | - | - |  |
| EmployeeAddress.Line2 | - | - | - | 0.95 | N/A | - | - |  |
| EmployeeAddress.State | - | - | - | 0.92 | N/A | - | - |  |
| EmployeeAddress.ZipCode | - | - | - | 0.94 | N/A | - | - |  |
| EmployeeName.FirstName | Elena | ✅ Elena | ✅ Elena | 0.95 | 1.0000 | 0.471,0.209,0.025,0.013 | 0.471,0.209,0.025,0.013 | ✅ |
| EmployeeName.LastName | Martinez | ✅ Martinez | ✅ Martinez | 0.90 | 1.0000 | 0.499,0.205,0.038,0.014 | 0.499,0.205,0.038,0.014 | ✅ |
| EmployeeName.MiddleName | - | - | - | 0.93 | N/A | - | - |  |
| EmployeeName.SuffixName | - | - | - | 0.94 | N/A | - | - |  |
| EmployeeNumber | EMP-78245 | ✅ EMP-78245 | ✅ EMP-78245 | 0.90 | 1.0000 | 0.473,0.228,0.053,0.016 | 0.473,0.228,0.052,0.016 | 🟡 |
| FederalFilingStatus | - | - | - | 0.94 | N/A | - | - |  |
| FederalTaxes.ItemDescription | Federal Income Tax | ❌ - | ✅ Federal Income Tax | - | 1.0000 | - | 0.533,0.357,0.072,0.017 | ❌ |
| FederalTaxes.Period | 152.10 | ❌ - | ✅ 152.10 | - | 1.0000 | - | 0.741,0.340,0.031,0.013 | ❌ |
| FederalTaxes.YTD | 1064.70 | ❌ - | ✅ 1064.70 | - | 1.0000 | - | 0.820,0.332,0.036,0.015 | ❌ |
| HolidayHourlyRate | - | - | - | 0.95 | N/A | - | - |  |
| PayDate | 2026-04-03 | ✅ 2026-04-03 | 🟡 04/03/2026 | 0.80 | 1.0000 | 0.709,0.201,0.044,0.014 | 0.709,0.201,0.044,0.014 | ✅ |
| PayPeriodEndDate | 2026-03-31 | ✅ 2026-03-31 | 🟡 03/31/2026 | 0.89 | 0.8700 | 0.759,0.223,0.041,0.013 | 0.759,0.224,0.040,0.013 | 🟡 |
| PayPeriodStartDate | 2026-03-16 | ✅ 2026-03-16 | 🟡 03/16/2026 | 0.88 | 0.8700 | 0.712,0.227,0.046,0.013 | 0.712,0.223,0.087,0.018 | ❌ |
| PayrollNumber | - | - | - | 0.95 | N/A | - | - |  |
| RegularHourlyRate | 16.88 | ✅ 16.88 | ✅ 16.88 | 0.95 | 1.0000 | 0.325,0.385,0.028,0.013 | 0.325,0.385,0.028,0.013 | ✅ |
| StateFilingStatus | - | - | - | 0.94 | N/A | - | - |  |
| StateTaxes.ItemDescription | State Income Tax | ❌ - | ✅ State Income Tax | - | 1.0000 | - | 0.535,0.382,0.065,0.016 | ❌ |
| StateTaxes.Period | 59.48 | ❌ - | ✅ 59.48 | - | 1.0000 | - | 0.748,0.364,0.026,0.013 | ❌ |
| StateTaxes.YTD | 416.36 | ❌ - | ✅ 416.36 | - | 1.0000 | - | 0.829,0.355,0.031,0.014 | ❌ |
| YTDCityTax | - | - | - | 0.95 | N/A | - | - |  |
| YTDFederalTax | 1064.70 | 🟡 1064.7 | ✅ 1064.70 | 0.96 | 1.0000 | 0.819,0.332,0.036,0.015 | 0.820,0.332,0.036,0.015 | 🟡 |
| YTDGrossPay | 9450.00 | 🟡 9450 | ✅ 9450.00 | 0.96 | 1.0000 | 0.481,0.610,0.047,0.020 | 0.470,0.370,0.038,0.015 | ❌ |
| YTDNetPay | 6562.92 | ✅ 6562.92 | ✅ 6562.92 | 0.95 | 1.0000 | 0.841,0.568,0.046,0.019 | 0.841,0.568,0.046,0.020 | 🟡 |
| YTDStateTax | 416.36 | ✅ 416.36 | ✅ 416.36 | 0.95 | 1.0000 | 0.829,0.355,0.031,0.014 | 0.829,0.355,0.031,0.014 | ✅ |
| YTDTotalDeductions | 2887.08 | ✅ 2887.08 | ✅ 2887.08 | 0.57 | 1.0000 | 0.844,0.523,0.037,0.016 | 0.844,0.523,0.037,0.016 | ✅ |
| are_field_names_sufficient | True | ✅ True | ❌ - | 0.07 | N/A | - | - |  |
| currency | USD | ✅ USD | ✅ USD | 0.92 | N/A | 0.182,0.288,0.013,0.012 | - | ❌ |
| is_gross_pay_valid | True | ✅ True | ❌ - | 0.92 | N/A | 0.481,0.610,0.047,0.020 | - | ❌ |
| is_ytd_gross_pay_highest | True | ✅ True | ❌ - | 0.92 | N/A | 0.481,0.610,0.047,0.020 | - | ❌ |


## synthetic-shelter-shelter-verification-render-spanish.png

**Durations**

- bda: 25.67s extraction
- llm: 2.511s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| assertion_text | - | Alaska Hills Property Management, LLC verifica que el inquilino que se indica a continuación reside en la propiedad que administramos y que es responsable del pago del alquiler en el importe y con la frecuencia que se detallan a continuación. | - | 0.59 | - | 0.103,0.269,0.767,0.047 | - | ❌ |
| author_name | - | Camila Ortega | - | 0.85 | - | 0.094,0.887,0.104,0.011 | - | ❌ |
| author_relationship | - | Administradora de la propiedad | - | 0.84 | - | 0.280,0.916,0.230,0.012 | - | ❌ |
| balance_due | - | - | - | - | N/A | - | - |  |
| contact_information | - | Tel: (907) 555-8124 Correo: cortega@alaskahillspm.com | - | 0.61 | - | 0.093,0.931,0.265,0.026 | - | ❌ |
| customer_name | - | Mateo Salazar | - | 0.91 | - | 0.409,0.353,0.110,0.009 | - | ❌ |
| has_signature | - | True | - | 0.86 | - | 0.096,0.844,0.277,0.042 | - | ❌ |
| landlord_name | - | - | ALASKA HILLS PROPERTY MANAGEMENT, LLC | - | 1.0000 | - | 0.242,0.269,0.343,0.013 | ❌ |
| lease_end_date | - | - | - | - | N/A | - | - |  |
| lease_start_date | - | - | 2024-03-15 | - | 0.9900 | - | 0.409,0.427,0.161,0.009 | ❌ |
| lease_type | - | - | Hasta nuevo aviso | - | 1.0000 | - | 0.743,0.546,0.135,0.009 | ❌ |
| payment_details.base_rent | - | - | 1050 | - | 1.0000 | - | 0.333,0.545,0.072,0.011 | ❌ |
| payment_details.fees | - | - | - | - | N/A | - | - |  |
| payment_details.total_monthly_payment | - | - | 1050 | - | 1.0000 | - | 0.333,0.545,0.072,0.011 | ❌ |
| payment_details.utilities | - | - | - | - | N/A | - | - |  |
| payment_due_day | - | - | 1 | - | 1.0000 | - | 0.272,0.678,0.083,0.009 | ❌ |
| property_address | - | - | 5121 Spruce Street, Unidad 2A, Anchorage, AK 99507 | - | N/A | - | 0.409,0.372,0.207,0.011 | ❌ |
| security_deposit | - | - | - | - | N/A | - | - |  |
| statement_date | - | 2026-09-08 | - | 0.73 | - | 0.333,0.180,0.205,0.012 | - | ❌ |
| statement_period.end_date | - | - | 2026-09-08 | - | 0.9900 | - | 0.333,0.180,0.205,0.012 | ❌ |
| statement_period.start_date | - | - | - | - | N/A | - | - |  |
| tenant_name | - | - | Mateo Salazar | - | 1.0000 | - | 0.409,0.353,0.111,0.010 | ❌ |


## synthetic-shelter-shelter-verification-render.pdf

**Durations**

- bda: 27.64s extraction
- llm: 1.586s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| assertion_text | - | Jordan Rivera has been residing at 1234 Cedar Lane, Apt 7B, New Haven, CT throughout the period of January 1, 2026, to August 31, 2026. Jordan Rivera is a tenant in good standing and has consistently paid rent in the amount of $1,120.00 each month during this period. | Jordan Rivera has been residing at 1234 Cedar Lane, Apt 7B, New Haven, CT throughout the period of January 1, 2026, to August 31, 2026. | 0.63 | N/A | 0.125,0.526,0.703,0.071 | 0.161,0.526,0.632,0.015 | ❌ |
| author_name | - | Cynthia Marshall | Cynthia Marshall | 0.93 | 0.8700 | 0.141,0.508,0.140,0.015 | 0.160,0.739,0.158,0.019 | ❌ |
| author_relationship | - | Property Manager | Property Manager | 0.70 | 1.0000 | 0.287,0.508,0.145,0.015 | 0.287,0.508,0.145,0.015 | ✅ |
| contact_information | - | Phone: (860) 555-0199 Email: cynthia.marshall@elmviewhomes.org | (860) 555-0199, cynthia.marshall@elmviewhomes.org | 0.85 | N/A | 0.656,0.097,0.081,0.012 | 0.605,0.097,0.044,0.015 | ❌ |
| customer_name | - | Jordan Rivera | Jordan Rivera | 0.94 | 1.0000 | 0.332,0.280,0.114,0.011 | 0.332,0.280,0.114,0.012 | 🟡 |
| has_signature | - | True | Yes | 0.90 | 0.8700 | 0.124,0.738,0.198,0.022 | 0.125,0.739,0.193,0.019 | ❌ |
| statement_date | - | 2026-09-05 | September 5, 2026 | 0.80 | 1.0000 | 0.307,0.187,0.155,0.014 | 0.307,0.187,0.155,0.014 | ✅ |


## synthetic-shelter-shelter-verification-scan.jpg

**Durations**

- bda: 17.13s extraction
- llm: 2.019s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| LINEITEMS.AMT | - | - | 1200.00 | - | 1.0000 | - | 0.658,0.446,0.165,0.027 | ❌ |
| LINEITEMS.PRODUCT_CODE | - | - | - | - | N/A | - | - |  |
| LINEITEMS.QTY | - | - | - | - | N/A | - | - |  |
| PAYMENTDETAILS.AMOUNTPAID | - | 1203 | 1203.00 | 0.90 | 1.0000 | 0.812,0.742,0.098,0.016 | 0.812,0.742,0.098,0.015 | 🟡 |
| PAYMENTDETAILS.SUBTOTAL | - | 1200 | 1200.00 | 0.18 | 1.0000 | 0.536,0.673,0.084,0.014 | 0.658,0.446,0.165,0.027 | ❌ |
| PAYMENTDETAILS.TAX | - | - | - | - | N/A | - | - |  |
| PAYMENTDETAILS.TOTAL | - | 1203 | 1203.00 | 0.89 | 1.0000 | 0.812,0.742,0.098,0.016 | 0.812,0.742,0.098,0.015 | 🟡 |
| RECEIPT_DATE | - | 09/06/2026 | 09/06/2026 | 0.91 | 1.0000 | 0.756,0.118,0.099,0.012 | 0.756,0.119,0.099,0.012 | 🟡 |
| RECEIPT_ID | - | MO-26-058714 | MO-26-058714 | 0.92 | 1.0000 | 0.756,0.092,0.143,0.012 | 0.756,0.092,0.143,0.012 | ✅ |
| VENDORDETAILS.VENDORADDRESS | - | 310 Seaside Avenue, Suite 101 New London, CT 06320 | 310 Seaside Avenue, Suite 101, New London, CT 06320 | 0.82 | N/A | 0.194,0.116,0.260,0.032 | 0.194,0.116,0.227,0.012 | ❌ |
| VENDORDETAILS.VENDORNAME | - | HARBOR COUNTY MONEY SERVICES | Harbor County Money Services | 0.83 | 1.0000 | 0.193,0.045,0.309,0.054 | 0.469,0.217,0.426,0.014 | ❌ |
| VENDORDETAILS.VENDORPHONE | - | (860) 555-2741 | (860) 555-2741 | 0.91 | 0.9900 | 0.258,0.153,0.126,0.015 | 0.258,0.153,0.234,0.015 | ❌ |
| expire | - | - | No | 0.85 | 1.0000 | 0.756,0.118,0.099,0.012 | 0.756,0.119,0.099,0.012 | 🟡 |


## synthetic-snap-income-proof-employment-wage-verification-letter-photo.png

**Durations**

- bda: 15.54s extraction
- llm: 1.051s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| employee_name | - | Luis Mendoza | Luis Mendoza | 0.90 | 0.9900 | 0.194,0.268,0.107,0.013 | 0.194,0.269,0.107,0.013 | 🟡 |
| employer_name | - | Harbor Home Care Services | Harbor Home Care Services | 0.94 | 1.0000 | 0.252,0.085,0.387,0.039 | 0.252,0.086,0.387,0.038 | 🟡 |
| employment_end_date | - | - | - | 0.93 | - | - | - |  |
| employment_start_date | - | August 12, 2024 | August 12, 2024 | 0.81 | 1.0000 | 0.413,0.423,0.124,0.014 | 0.413,0.423,0.124,0.013 | 🟡 |
| issuer_name | - | Dana Whitfield | Dana Whitfield | 0.95 | 1.0000 | 0.264,0.685,0.124,0.030 | 0.178,0.685,0.210,0.029 | ❌ |
| issuer_title | - | Human Resources Manager | Human Resources Manager | 0.93 | 1.0000 | 0.179,0.755,0.197,0.020 | 0.179,0.757,0.197,0.015 | ❌ |
| job_title | - | Home Health Aide | Home Health Aide | 0.89 | 1.0000 | 0.223,0.420,0.143,0.013 | 0.223,0.420,0.143,0.012 | 🟡 |
| salary_or_wage | - | $19.00 per hour | $19.00 per hour | 0.35 | 1.0000 | 0.538,0.456,0.116,0.014 | 0.450,0.455,0.204,0.014 | ❌ |


## synthetic-snap-income-proof-employment-wage-verification-letter-rendered.png

**Durations**

- bda: 16.59s extraction
- llm: 1.032s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| employee_name | Luis Mendoza | ✅ Luis Mendoza | ✅ Luis Mendoza | 0.90 | 1.0000 | 0.119,0.291,0.120,0.012 | 0.119,0.291,0.120,0.012 | ✅ |
| employer_name | Harbor Home Care Services | ✅ Harbor Home Care Services | ✅ Harbor Home Care Services | 0.94 | 1.0000 | 0.179,0.064,0.455,0.028 | 0.179,0.064,0.455,0.028 | ✅ |
| employment_end_date | - | - | - | 0.93 | - | - | - |  |
| employment_start_date | August 12, 2024 | ✅ August 12, 2024 | ✅ August 12, 2024 | 0.81 | 1.0000 | 0.368,0.466,0.143,0.015 | 0.368,0.466,0.143,0.015 | ✅ |
| issuer_name | Dana Whitfield | ✅ Dana Whitfield | ✅ Dana Whitfield | 0.95 | 1.0000 | 0.210,0.765,0.132,0.029 | 0.117,0.762,0.225,0.032 | ❌ |
| issuer_title | Human Resources Manager | ✅ Human Resources Manager | ✅ Human Resources Manager | 0.92 | 1.0000 | 0.121,0.841,0.209,0.014 | 0.121,0.841,0.209,0.014 | ✅ |
| job_title | Home Health Aide | ✅ Home Health Aide | ✅ Home Health Aide | 0.89 | 1.0000 | 0.158,0.465,0.157,0.012 | 0.158,0.466,0.157,0.012 | 🟡 |
| salary_or_wage | $19.00 per hour | ✅ $19.00 per hour | ✅ $19.00 per hour | 0.34 | 1.0000 | 0.512,0.503,0.136,0.016 | 0.410,0.503,0.238,0.016 | ❌ |
