# synthetic-shelter-shelter-verification-render.pdf


_Run: 2026-10-01 01:41 UTC_


## Durations

- bda: 29.62s extraction
- ocr-mapping: 1.792s extraction


## Cost

_By Service_
- us.amazon.nova-pro-v1:0: $0.01212480
- bda: $0.04000000
- **total: $0.05212480**

_By Extraction Method_
- shared (preclassification): $0.00882720
- ocr-mapping extraction: $0.00329760
- primary (bda): $0.04000000
- **total: $0.05212480**


## Accuracy

_By Extracted Data_
- BDA: 100% equivalent, 100% close, 0% misses
- OCR Mapping: 71% equivalent, 71% close, 29% misses

_By Bounding Box_
- BDA: 0/3 exact, 3 miss
- OCR Mapping: 0/3 exact, 3 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Bounding Box | BDA Bounding Box | LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| assertion_text | Jordan Rivera has been residing at 1234 Cedar Lane, Apt 7B, New Haven, CT throughout the period of January 1, 2026, to August 31, 2026. Jordan Rivera is a tenant in good standing and has consistently paid rent in the amount of $1,120.00 each month during this period. | ✅ Jordan Rivera has been residing at 1234 Cedar Lane, Apt 7B, New Haven, CT throughout the period of January 1, 2026, to August 31, 2026. Jordan Rivera is a tenant in good standing and has consistently paid rent in the amount of $1,120.00 each month during this period. | ❌ Jordan Rivera has been residing at 1234 Cedar Lane, Apt 7B, New Haven, CT throughout the period of January 1, 2026, to August 31, 2026. | 0.64 | N/A | - | 0.125,0.526,0.703,0.071 | 0.161,0.526,0.632,0.015 |
| author_name | Cynthia Marshall | ✅ Cynthia Marshall | ✅ Cynthia Marshall | 0.93 | 0.8700 | 0.127,0.773,0.136,0.014 | ❌ 0.141,0.508,0.140,0.015 | ❌ 0.160,0.739,0.158,0.019 |
| author_relationship | Property Manager | ✅ Property Manager | ✅ Property Manager | 0.70 | 1.0000 | 0.127,0.792,0.147,0.013 | ❌ 0.287,0.508,0.145,0.015 | ❌ 0.287,0.508,0.145,0.015 |
| contact_information | Phone: (860) 555-0199 Email: cynthia.marshall@elmviewhomes.org | ✅ Phone: (860) 555-0199 Email: cynthia.marshall@elmviewhomes.org | ❌ (860) 555-0199, cynthia.marshall@elmviewhomes.org | 0.85 | 0.9800 | - | 0.656,0.097,0.081,0.012 | 0.190,0.828,0.126,0.014 |
| customer_name | Jordan Rivera | ✅ Jordan Rivera | ✅ Jordan Rivera | 0.94 | 1.0000 | - | 0.332,0.280,0.114,0.011 | 0.332,0.280,0.114,0.012 |
| has_signature | True | ✅ True | ✅ True | 0.90 | 0.8700 | - | 0.124,0.738,0.198,0.022 | 0.125,0.739,0.193,0.019 |
| statement_date | 2026-09-05 | ✅ 2026-09-05 | ✅ 2026-09-05 | 0.80 | 1.0000 | 0.127,0.188,0.334,0.013 | ❌ 0.307,0.187,0.155,0.014 | ❌ 0.307,0.187,0.155,0.014 |
