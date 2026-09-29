# synthetic-expense-child-support-scan.jpg


_Run: 2026-09-29 00:53 UTC_


## Durations

- bda: 26.87s extraction
- llm: 2.26s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012360 (1956 in / 26 out)
- us.amazon.nova-pro-v1:0: $0.01543840 (16622 in / 669 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05556200**

_By Extraction Method_
- shared (preclassification): $0.00927240
- llm extraction: $0.00628960
- primary (bda): $0.04000000
- **total: $0.05556200**


## Accuracy
- BDA: 100% equivalent, 100% close, 0% misses
- LLM: 93% equivalent, 93% close, 7% misses


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| case_number | D-2022-04567-FC | ✅ D-2022-04567-FC | ✅ D-2022-04567-FC | 0.89 | 1.0000 | 0.711,0.190,0.118,0.009 | 0.711,0.190,0.118,0.009 | ✅ |
| child_name | - | - | - | 0.91 | - | - | - |  |
| court_name | 2nd Judicial District Court | ✅ 2nd Judicial District Court | ✅ 2nd Judicial District Court | 0.67 | 1.0000 | 0.711,0.227,0.168,0.009 | 0.710,0.227,0.168,0.009 | 🟡 |
| effective_end_date | - | - | - | 0.90 | - | - | - |  |
| effective_start_date | 2022-03-22 | ✅ 2022-03-22 | ✅ 2022-03-22 | 0.77 | 1.0000 | 0.355,0.361,0.073,0.009 | 0.356,0.361,0.073,0.009 | 🟡 |
| order_date | 2022-03-15 | ✅ 2022-03-15 | ✅ 2022-03-15 | 0.92 | 1.0000 | 0.711,0.208,0.074,0.009 | 0.711,0.208,0.074,0.009 | ✅ |
| payer_name | Daniel R. Montoya | ✅ Daniel R. Montoya | ✅ Daniel R. Montoya | 0.93 | 1.0000 | 0.712,0.282,0.123,0.011 | 0.711,0.282,0.123,0.011 | 🟡 |
| payment_amount | 500.00 | ✅ 500 | ✅ 500.00 | 0.89 | 1.0000 | 0.356,0.300,0.053,0.010 | 0.356,0.300,0.052,0.010 | 🟡 |
| payment_frequency | Weekly | ✅ Weekly | ✅ Weekly | 0.89 | 1.0000 | 0.355,0.315,0.049,0.011 | 0.097,0.300,0.048,0.011 | ❌ |
| payment_type | Child Support | ✅ Child Support | ✅ Child Support | 0.84 | 1.0000 | 0.711,0.264,0.133,0.011 | 0.711,0.264,0.134,0.011 | 🟡 |
| recipient_address | 123 Desert Sage Rd, Apt 4B, Albuquerque, NM 87108 | ✅ 123 Desert Sage Rd, Apt 4B Albuquerque, NM 87108 | ❌ 123 Desert Sage Rd, Apt 4B, Albuquerque, NM | 0.79 | 1.0000 | 0.097,0.226,0.188,0.029 | 0.098,0.226,0.186,0.011 | ❌ |
| recipient_name.first_name | Maria | ✅ Maria | ✅ Maria | 0.02 | 1.0000 | 0.098,0.189,0.084,0.009 | 0.098,0.189,0.039,0.009 | ❌ |
| recipient_name.last_name | Lopez | ✅ Lopez | ✅ Lopez | 0.89 | 1.0000 | 0.186,0.189,0.043,0.011 | 0.186,0.189,0.043,0.011 | ✅ |
| recipient_name.middle_name | Elena | ✅ Elena | ✅ Elena | 0.28 | 1.0000 | 0.142,0.189,0.039,0.009 | 0.142,0.189,0.039,0.009 | ✅ |
| recipient_state | NM | ✅ NM | ✅ NM | 0.89 | 1.0000 | 0.192,0.244,0.022,0.009 | 0.537,0.114,0.029,0.010 | ❌ |
| recipient_zip_code | 87108 | ✅ 87108 | ✅ 87108 | 0.90 | 1.0000 | 0.222,0.244,0.041,0.009 | 0.221,0.244,0.041,0.009 | 🟡 |
