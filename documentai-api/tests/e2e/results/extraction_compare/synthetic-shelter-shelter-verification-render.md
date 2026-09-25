_Run: 2026-09-25 16:59 UTC_


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
