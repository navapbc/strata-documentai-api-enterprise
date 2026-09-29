# synthetic-shelter-shelter-verification-render.pdf


_Run: 2026-09-29 16:10 UTC_


## Durations

- bda: 26.81s extraction
- llm: 2.45s extraction


## Cost

_By Service_
- us.amazon.nova-pro-v1:0: $0.01238720 (13056 in / 607 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05238720**

_By Extraction Method_
- shared (preclassification): $0.00882720
- llm extraction: $0.00356000
- primary (bda): $0.04000000
- **total: $0.05238720**


## Accuracy
- BDA: 100% equivalent, 100% close, 0% misses
- LLM: 86% equivalent, 86% close, 14% misses


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| assertion_text | Jordan Rivera has been residing at 1234 Cedar Lane, Apt 7B, New Haven, CT throughout the period of January 1, 2026, to August 31, 2026. Jordan Rivera is a tenant in good standing and has consistently paid rent in the amount of $1,120.00 each month during this period. | ✅ Jordan Rivera has been residing at 1234 Cedar Lane, Apt 7B, New Haven, CT throughout the period of January 1, 2026, to August 31, 2026. Jordan Rivera is a tenant in good standing and has consistently paid rent in the amount of $1,120.00 each month during this period. | ✅ Jordan Rivera has been residing at 1234 Cedar Lane, Apt 7B, New Haven, CT throughout the period of January 1, 2026, to August 31, 2026. Jordan Rivera is a tenant in good standing and has consistently paid rent in the amount of $1,120.00 each month during this period. | 0.64 | N/A | 0.125,0.526,0.703,0.071 | 0.125,0.545,0.703,0.015 | ❌ |
| author_name | Cynthia Marshall | ✅ Cynthia Marshall | ✅ Cynthia Marshall | 0.93 | 0.8700 | 0.141,0.508,0.140,0.015 | 0.160,0.739,0.158,0.019 | ❌ |
| author_relationship | Property Manager | ✅ Property Manager | ✅ Property Manager | 0.70 | 1.0000 | 0.287,0.508,0.145,0.015 | 0.287,0.508,0.145,0.015 | ✅ |
| contact_information | Phone: (860) 555-0199 Email: cynthia.marshall@elmviewhomes.org | ✅ Phone: (860) 555-0199 Email: cynthia.marshall@elmviewhomes.org | ❌ (860) 555-0199, cynthia.marshall@elmviewhomes.org | 0.83 | 0.9800 | 0.656,0.097,0.081,0.012 | 0.190,0.828,0.126,0.014 | ❌ |
| customer_name | Jordan Rivera | ✅ Jordan Rivera | ✅ Jordan Rivera | 0.94 | 1.0000 | 0.332,0.280,0.114,0.011 | 0.332,0.280,0.114,0.012 | 🟡 |
| has_signature | True | ✅ True | ✅ True | 0.90 | 0.8700 | 0.124,0.738,0.198,0.022 | 0.125,0.739,0.193,0.019 | ❌ |
| statement_date | 2026-09-05 | ✅ 2026-09-05 | ✅ 2026-09-05 | 0.80 | 1.0000 | 0.307,0.187,0.155,0.014 | 0.307,0.187,0.155,0.014 | ✅ |
