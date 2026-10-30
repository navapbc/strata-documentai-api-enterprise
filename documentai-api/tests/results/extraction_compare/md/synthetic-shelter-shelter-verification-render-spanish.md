# synthetic-shelter-shelter-verification-render-spanish.png

_Last run: 2026-10-30 03:19 UTC_

## Durations

- bda: 28.06s extraction
- llm: 2.353s extraction

## Cost

_By Service_

- us.amazon.nova-lite-v1:0: $0.00012384 (1956 in / 27 out)
- us.amazon.nova-pro-v1:0: $0.01507760 (16039 in / 702 out)
- bda: $0.04000000 (1 page(s))
- analyze_document_layout: $0.00400000 (1 page(s))
- **total: $0.05920144**

_By Extraction Method_

- shared (preclassification): $0.00932064
- ocr-mapping extraction: $0.00988080
- primary (bda): $0.04000000
- **total: $0.05920144**

## Accuracy

_By Extracted Data_

- BDA: 0/7 (0%) equivalent match, 0/7 (0%) close, 7 misses
- OCR Mapping: 0/7 (0%) equivalent match, 0/7 (0%) close, 7 misses

_By Bounding Box_

- BDA: 0/3 (0%) exact, 3 miss
- OCR Mapping: 0/3 (0%) exact, 3 miss

## Field Comparison

| Field | Expected | BDA Value | OCR / LLM Value | BDA Conf | OCR / LLM Conf | Expected Bounding Box | BDA Bounding Box | OCR / LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| assertion_text | Por la presente, Alaska Hills Property Management, LLC verifica que el inquilino que se indica a continuación reside en la propiedad que administramos y que es responsable del pago del alquiler en el importe y con la frecuencia que se detallan a continuación. | ❌ - | ❌ - | - | - | - | - | - |
| author_name | Camila Ortega | ❌ - | ❌ - | - | - | - | - | - |
| author_relationship | Administradora de Propiedades | ❌ - | ❌ - | - | - | 0.094,0.902,0.229,0.011 | ❌ - | ❌ - |
| balance_due | N/A | - | - | 0.91 | N/A | - | - | - |
| contact_information | Tel: (907) 555-8124 Correo: cortega@alaskahillspm.com | ❌ - | ❌ - | - | - | - | - | - |
| customer_name | Mateo Salazar | ❌ - | ❌ - | - | - | 0.409,0.353,0.109,0.009 | ❌ - | ❌ - |
| has_signature | True | ❌ - | ❌ - | - | - | - | - | - |
| landlord_name | N/A | Alaska Hills Property Management, LLC | ALASKA HILLS PROPERTY MANAGEMENT, LLC | 0.64 | 1.0000 | - | 0.198,0.035,0.299,0.045 | 0.242,0.269,0.343,0.013 |
| lease_end_date | N/A | - | - | 0.88 | N/A | - | - | - |
| lease_start_date | N/A | 2024-03-15 | 2024-03-15 | 0.75 | 0.9900 | - | 0.409,0.428,0.018,0.010 | 0.409,0.427,0.161,0.009 |
| lease_type | N/A | - | Apartamento de 1 dormitorio / 1 baño | 0.89 | 0.9600 | - | - | 0.408,0.446,0.293,0.011 |
| payment_details.base_rent | N/A | 1050.00 | 1050 | 0.57 | 1.0000 | - | 0.333,0.545,0.072,0.011 | 0.333,0.545,0.072,0.011 |
| payment_details.fees | N/A | - | - | 0.91 | N/A | - | - | - |
| payment_details.total_monthly_payment | N/A | - | 1050 | 0.88 | 1.0000 | - | - | 0.333,0.545,0.072,0.011 |
| payment_details.utilities | N/A | - | - | 0.88 | N/A | - | - | - |
| payment_due_day | N/A | 1 | 1 | 0.01 | 1.0000 | - | 0.538,0.446,0.006,0.009 | 0.469,0.546,0.062,0.009 |
| property_address | N/A | 5121 Spruce Street, Unidad 2A, Anchorage, AK 99507 | 5121 Spruce Street, Unidad 2A, Anchorage, AK 99507 | 0.64 | 1.0000 | - | 0.408,0.372,0.234,0.028 | 0.409,0.372,0.233,0.011 |
| security_deposit | N/A | - | - | 0.90 | N/A | - | - | - |
| statement_date | 2026-09-08 | ❌ - | ❌ - | - | - | 0.734,0.895,0.175,0.010 | ❌ - | ❌ - |
| statement_period.end_date | N/A | - | 2026-09-08 | 0.77 | 0.9900 | - | - | 0.333,0.180,0.205,0.012 |
| statement_period.start_date | N/A | - | - | 0.87 | N/A | - | - | - |
| tenant_name | N/A | Mateo Salazar | Mateo Salazar | 0.91 | 1.0000 | - | 0.409,0.353,0.110,0.010 | 0.409,0.353,0.111,0.010 |