# synthetic-shelter-shelter-verification-scan.jpg

_Last run: 2026-10-30 03:20 UTC_

## Durations

- bda: 25.64s extraction
- llm: 3.059s extraction

## Cost

_By Service_

- us.amazon.nova-lite-v1:0: $0.00012384 (1956 in / 27 out)
- us.amazon.nova-pro-v1:0: $0.01429200 (15069 in / 699 out)
- bda: $0.04000000 (1 page(s))
- analyze_document_layout: $0.00400000 (1 page(s))
- **total: $0.05841584**

_By Extraction Method_

- shared (preclassification): $0.00927264
- ocr-mapping extraction: $0.00914320
- primary (bda): $0.04000000
- **total: $0.05841584**

## Accuracy

_By Extracted Data_

- BDA: 0/10 (0%) equivalent match, 0/10 (0%) close, 10 misses
- OCR Mapping: 8/10 (80%) equivalent match, 8/10 (80%) close, 2 misses

_By Bounding Box_

- BDA: 0/5 (0%) exact, 5 miss
- OCR Mapping: 4/5 (80%) exact, 1 miss

## Field Comparison

| Field | Expected | BDA Value | OCR / LLM Value | BDA Conf | OCR / LLM Conf | Expected Bounding Box | BDA Bounding Box | OCR / LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| LINEITEMS.AMT | 1200.00 | ❌ - | ❌ 1200.00, 3.00 | - | N/A | - | - | 0.658,0.446,0.165,0.027 |
| LINEITEMS.PRODUCT_CODE | - | - | - | - | N/A | - | - | - |
| LINEITEMS.QTY | - | - | - | - | N/A | - | - | - |
| PAYMENTDETAILS.AMOUNTPAID | 1203.00 | ❌ - | ✅ 1203.00 | - | 1.0000 | 0.812,0.742,0.097,0.015 | ❌ - | ✅ 0.812,0.742,0.098,0.015 |
| PAYMENTDETAILS.SUBTOTAL | 1200.00 | ❌ - | ✅ 1200.00 | - | 1.0000 | - | - | 0.658,0.446,0.165,0.027 |
| PAYMENTDETAILS.TAX | - | - | - | - | N/A | - | - | - |
| PAYMENTDETAILS.TOTAL | 1203.00 | ❌ - | ✅ 1203.00 | - | 1.0000 | 0.812,0.742,0.097,0.015 | ❌ - | ✅ 0.812,0.742,0.098,0.015 |
| RECEIPT_DATE | 2026-09-06 | ❌ - | ✅ 2026-09-06 | - | 1.0000 | 0.756,0.118,0.098,0.012 | ❌ - | ✅ 0.756,0.119,0.099,0.012 |
| RECEIPT_ID | MO-26-058714 | ❌ - | ✅ MO-26-058714 | - | 1.0000 | 0.756,0.092,0.142,0.010 | ❌ - | ✅ 0.756,0.092,0.143,0.012 |
| VENDORDETAILS.VENDORADDRESS | 310 Seaside Avenue, Suite 101, New London, CT 06320 | ❌ - | ✅ 310 Seaside Avenue, Suite 101, New London, CT 06320 | - | N/A | - | - | 0.194,0.116,0.260,0.012 |
| VENDORDETAILS.VENDORNAME | Harbor County Money Services | ❌ - | ✅ Harbor County Money Services | - | 1.0000 | - | - | 0.469,0.217,0.426,0.014 |
| VENDORDETAILS.VENDORPHONE | (860) 555-2741 | ❌ - | ✅ (860) 555-2741 | - | 0.9900 | 0.194,0.146,0.544,0.021 | ❌ - | ❌ 0.258,0.153,0.234,0.015 |
| amount | N/A | 1200 | - | 0.66 | - | - | 0.812,0.742,0.098,0.016 | - |
| amount_overdue | N/A | - | - | 0.93 | - | - | - | - |
| document_type | N/A | Money Order Receipt | - | 0.91 | - | - | 0.612,0.053,0.310,0.016 | - |
| expire | No | ❌ - | ❌ True | - | 1.0000 | - | - | 0.756,0.119,0.099,0.012 |
| payee_or_provider_name | N/A | Seaside Village Apartments | - | 0.83 | - | - | 0.568,0.334,0.281,0.016 | - |
| payer_name | N/A | Elias Morgan | - | 0.94 | - | - | 0.164,0.285,0.116,0.014 | - |
| receipt_or_notice_date | N/A | - | - | 0.84 | - | - | - | - |
| reference_number | N/A | MO-26-058714 | - | 0.89 | - | - | 0.756,0.092,0.143,0.011 | - |
| service_period_end | N/A | 2026-09-30 | - | 0.91 | - | - | 0.297,0.578,0.169,0.014 | - |
| service_period_start | N/A | 2026-09-01 | - | 0.86 | - | - | 0.065,0.578,0.156,0.014 | - |