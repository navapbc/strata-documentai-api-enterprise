# synthetic-shelter-shelter-verification-scan.jpg


_Run: 2026-09-29 20:01 UTC_


## Durations

- bda: 18.18s extraction
- ocr-mapping: 2.434s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384 (1956 in / 27 out)
- us.amazon.nova-pro-v1:0: $0.01408080 (15069 in / 633 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05420464**

_By Extraction Method_
- shared (preclassification): $0.00926624
- ocr-mapping extraction: $0.00493840
- primary (bda): $0.04000000
- **total: $0.05420464**


## Accuracy
- BDA: 80% equivalent, 80% close, 20% misses
- OCR Mapping: 60% equivalent, 60% close, 40% misses


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| LINEITEMS.AMT | 1200.00 | ❌ - | ✅ 1200.00 | - | 1.0000 | - | 0.658,0.446,0.165,0.027 | ❌ |
| LINEITEMS.PRODUCT_CODE | - | - | - | - | N/A | - | - |  |
| LINEITEMS.QTY | - | - | - | - | N/A | - | - |  |
| PAYMENTDETAILS.AMOUNTPAID | 1203.00 | ✅ 1203 | ✅ 1203.00 | 0.90 | 1.0000 | 0.812,0.742,0.098,0.016 | 0.812,0.742,0.098,0.015 | 🟡 |
| PAYMENTDETAILS.SUBTOTAL | 1200.00 | ✅ 1200 | ✅ 1200.00 | 0.19 | 1.0000 | 0.821,0.673,0.084,0.014 | 0.658,0.446,0.165,0.027 | ❌ |
| PAYMENTDETAILS.TAX | - | - | - | - | N/A | - | - |  |
| PAYMENTDETAILS.TOTAL | 1203.00 | ✅ 1203 | ✅ 1203.00 | 0.89 | 1.0000 | 0.812,0.742,0.098,0.016 | 0.812,0.742,0.098,0.015 | 🟡 |
| RECEIPT_DATE | 2026-09-06 | ✅ 09/06/2026 | ✅ 2026-09-06 | 0.91 | 1.0000 | 0.756,0.118,0.099,0.013 | 0.756,0.119,0.099,0.012 | 🟡 |
| RECEIPT_ID | MO-26-058714 | ✅ MO-26-058714 | ✅ MO-26-058714 | 0.92 | 1.0000 | 0.756,0.092,0.143,0.011 | 0.756,0.092,0.143,0.012 | 🟡 |
| VENDORDETAILS.VENDORADDRESS | 310 Seaside Avenue, Suite 101, New London, CT 06320 | ✅ 310 Seaside Avenue, Suite 101 New London, CT 06320 | ❌ 275 Ocean Avenue, New London, CT 06320 | 0.82 | N/A | 0.194,0.116,0.260,0.032 | 0.194,0.135,0.204,0.012 | ❌ |
| VENDORDETAILS.VENDORNAME | Harbor County Money Services | ✅ HARBOR COUNTY MONEY SERVICES | ❌ Seaside Village Apartments | 0.84 | 1.0000 | 0.193,0.045,0.309,0.054 | 0.568,0.334,0.281,0.016 | ❌ |
| VENDORDETAILS.VENDORPHONE | (860) 555-2741 | ✅ (860) 555-2741 | ❌ - | 0.91 | N/A | 0.258,0.153,0.126,0.015 | - | ❌ |
| expire | No | ❌ - | ❌ - | 0.86 | N/A | 0.756,0.118,0.099,0.013 | - | ❌ |
