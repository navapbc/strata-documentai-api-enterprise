# synthetic-shelter-shelter-verification-render-spanish.png


_Run: 2026-10-01 02:38 UTC_


## Durations

- bda: 27.21s extraction
- ocr-mapping: 2.253s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012408
- us.amazon.nova-pro-v1:0: $0.01278000
- bda: $0.04000000
- **total: $0.05290408**

_By Extraction Method_
- shared (preclassification): $0.00926648
- ocr-mapping extraction: $0.00363760
- primary (bda): $0.04000000
- **total: $0.05290408**


## Accuracy

_By Extracted Data_
- BDA: 5/7 (71%) equivalent match, 7/7 (100%) close, 0 misses
- OCR Mapping: 3/7 (43%) equivalent match, 6/7 (86%) close, 1 miss

_By Bounding Box_
- BDA: 1/3 exact, 2 miss
- OCR Mapping: 1/3 exact, 2 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Bounding Box | BDA Bounding Box | LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| assertion_text | Por la presente, Alaska Hills Property Management, LLC verifica que el inquilino que se indica a continuación reside en la propiedad que administramos y que es responsable del pago del alquiler en el importe y con la frecuencia que se detallan a continuación. | 🟡 Alaska Hills Property Management, LLC verifica que el inquilino que se indica a continuación reside en la propiedad que administramos y que es responsable del pago del alquiler en el importe y con la frecuencia que se detallan a continuación. | 🟡 Alaska Hills Property Management, LLC verifica que el inquilino que se indica a continuación reside en la propiedad que administramos y que es responsable del pago del alquiler en el importe y con la frecuencia que se detallan a continuación. | 0.60 | N/A | - | 0.103,0.269,0.767,0.047 | 0.103,0.303,0.694,0.013 |
| author_name | Camila Ortega | ✅ Camila Ortega | ✅ Camila Ortega | 0.85 | 0.9900 | - | 0.094,0.887,0.104,0.011 | 0.096,0.845,0.275,0.041 |
| author_relationship | Administradora de Propiedades | 🟡 Administradora de la propiedad | 🟡 Administradora de la propiedad | 0.84 | 0.9900 | 0.094,0.902,0.229,0.011 | ❌ 0.280,0.916,0.230,0.012 | ❌ 0.280,0.916,0.230,0.011 |
| contact_information | Tel: (907) 555-8124 Correo: cortega@alaskahillspm.com | ✅ Tel: (907) 555-8124 Correo: cortega@alaskahillspm.com | 🟡 (907) 555-8124, cortega@alaskahillspm.com | 0.61 | 0.8400 | - | 0.093,0.931,0.265,0.026 | 0.607,0.062,0.312,0.012 |
| customer_name | Mateo Salazar | ✅ Mateo Salazar | ✅ Mateo Salazar | 0.91 | 1.0000 | 0.409,0.353,0.109,0.009 | ✅ 0.409,0.353,0.110,0.009 | ✅ 0.409,0.353,0.111,0.010 |
| has_signature | True | ✅ True | ❌ False | 0.86 | 1.0000 | - | 0.096,0.844,0.277,0.042 | 0.093,0.902,0.230,0.011 |
| statement_date | 2026-09-08 | ✅ 2026-09-08 | ✅ 2026-09-08 | 0.73 | 0.9900 | 0.734,0.895,0.175,0.010 | ❌ 0.333,0.180,0.205,0.012 | ❌ 0.333,0.180,0.205,0.012 |
