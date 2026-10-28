# synthetic-shelter-shelter-verification-render-spanish.png


_Run: 2026-10-28 18:36 UTC_


## Durations

- bda: 24.14s extraction
- ocr-mapping: 2.875s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012408 (1956 in / 28 out)
- us.amazon.nova-pro-v1:0: $0.01506480 (16039 in / 698 out)
- bda: $0.04000000 (1 page(s))
- analyze_document_layout: $0.00400000 (1 page(s))
- **total: $0.05918888**

_By Extraction Method_
- shared (preclassification): $0.00930808
- ocr-mapping extraction: $0.00988080
- primary (bda): $0.04000000
- **total: $0.05918888**


## Accuracy

_By Extracted Data_
- BDA: 5/7 (71%) equivalent match, 7/7 (100%) close, 0 misses
- OCR Mapping: 0/7 (0%) equivalent match, 0/7 (0%) close, 7 misses

_By Bounding Box_
- BDA: 1/3 exact, 2 miss
- OCR Mapping: 0/3 exact, 3 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Bounding Box | BDA Bounding Box | LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| assertion_text | Por la presente, Alaska Hills Property Management, LLC verifica que el inquilino que se indica a continuación reside en la propiedad que administramos y que es responsable del pago del alquiler en el importe y con la frecuencia que se detallan a continuación. | 🟡 Alaska Hills Property Management, LLC verifica que el inquilino que se indica a continuación reside en la propiedad que administramos y que es responsable del pago del alquiler en el importe y con la frecuencia que se detallan a continuación. | ❌ - | 0.60 | - | - | 0.103,0.269,0.767,0.047 | - |
| author_name | Camila Ortega | ✅ Camila Ortega | ❌ - | 0.85 | - | - | 0.094,0.887,0.104,0.011 | - |
| author_relationship | Administradora de Propiedades | 🟡 Administradora de la propiedad | ❌ - | 0.84 | - | 0.094,0.902,0.229,0.011 | ❌ 0.280,0.916,0.230,0.012 | ❌ - |
| balance_due | N/A | - | - | - | N/A | - | - | - |
| contact_information | Tel: (907) 555-8124 Correo: cortega@alaskahillspm.com | ✅ Tel: (907) 555-8124 Correo: cortega@alaskahillspm.com | ❌ - | 0.61 | - | - | 0.093,0.931,0.265,0.026 | - |
| customer_name | Mateo Salazar | ✅ Mateo Salazar | ❌ - | 0.91 | - | 0.409,0.353,0.109,0.009 | ✅ 0.409,0.353,0.110,0.009 | ❌ - |
| has_signature | True | ✅ True | ❌ - | 0.86 | - | - | 0.096,0.844,0.277,0.042 | - |
| landlord_name | N/A | - | ALASKA HILLS PROPERTY MANAGEMENT, LLC | - | 1.0000 | - | - | 0.242,0.269,0.343,0.013 |
| lease_end_date | N/A | - | - | - | N/A | - | - | - |
| lease_start_date | N/A | - | 2024-03-15 | - | 0.9900 | - | - | 0.409,0.427,0.161,0.009 |
| lease_type | N/A | - | Apartamento de 1 dormitorio / 1 baño | - | 0.9600 | - | - | 0.408,0.446,0.293,0.011 |
| payment_details.base_rent | N/A | - | 1050 | - | 1.0000 | - | - | 0.333,0.545,0.072,0.011 |
| payment_details.fees | N/A | - | - | - | N/A | - | - | - |
| payment_details.total_monthly_payment | N/A | - | 1050 | - | 1.0000 | - | - | 0.333,0.545,0.072,0.011 |
| payment_details.utilities | N/A | - | - | - | N/A | - | - | - |
| payment_due_day | N/A | - | 1 | - | 1.0000 | - | - | 0.469,0.546,0.062,0.009 |
| property_address | N/A | - | 5121 Spruce Street, Unidad 2A, Anchorage, AK 99507 | - | 1.0000 | - | - | 0.409,0.372,0.233,0.011 |
| security_deposit | N/A | - | - | - | N/A | - | - | - |
| statement_date | 2026-09-08 | ✅ 2026-09-08 | ❌ - | 0.73 | - | 0.734,0.895,0.175,0.010 | ❌ 0.333,0.180,0.205,0.012 | ❌ - |
| statement_period.end_date | N/A | - | 2026-09-08 | - | 0.9900 | - | - | 0.333,0.180,0.205,0.012 |
| statement_period.start_date | N/A | - | - | - | N/A | - | - | - |
| tenant_name | N/A | - | Mateo Salazar | - | 1.0000 | - | - | 0.409,0.353,0.111,0.010 |
