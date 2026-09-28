# synthetic-shelter-shelter-verification-render-spanish.png


_Run: 2026-09-28 18:39 UTC_


## Durations

- bda: 36.72s extraction
- llm: 2.562s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00012384 (1956 in / 27 out)
- us.amazon.nova-pro-v1:0: $0.01260480 (13716 in / 510 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.05272864**

_By Extraction Method_
- shared (preclassification): $0.00929184
- llm extraction: $0.00343680
- primary (bda): $0.04000000
- **total: $0.05272864**


## Accuracy
- BDA: 71% exact, 71% loose, 29% misses
- LLM: 43% exact, 43% loose, 57% misses


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| assertion_text | Por la presente, Alaska Hills Property Management, LLC verifica que el inquilino que se indica a continuación reside en la propiedad que administramos y que es responsable del pago del alquiler en el importe y con la frecuencia que se detallan a continuación. | ❌ Alaska Hills Property Management, LLC verifica que el inquilino que se indica a continuación reside en la propiedad que administramos y que es responsable del pago del alquiler en el importe y con la frecuencia que se detallan a continuación. | ❌ Alaska Hills Property Management, LLC verifica que el inquilino reside en la propiedad y es responsable del pago del alquiler. | 0.60 | N/A | 0.103,0.269,0.767,0.047 | 0.103,0.303,0.694,0.013 | ❌ |
| author_name | Camila Ortega | ✅ Camila Ortega | ✅ Camila Ortega | 0.85 | 0.9900 | 0.094,0.887,0.104,0.011 | 0.096,0.845,0.275,0.041 | ❌ |
| author_relationship | Administradora de Propiedades | ❌ Administradora de la propiedad | ❌ Administradora de la propiedad | 0.84 | 0.9900 | 0.280,0.916,0.230,0.012 | 0.280,0.916,0.230,0.011 | 🟡 |
| contact_information | Tel: (907) 555-8124 Correo: cortega@alaskahillspm.com | ✅ Tel: (907) 555-8124 Correo: cortega@alaskahillspm.com | ✅ Tel: (907) 555-8124 Correo: cortega@alaskahillspm.com | 0.61 | 0.8400 | 0.093,0.931,0.265,0.026 | 0.607,0.062,0.312,0.012 | ❌ |
| customer_name | Mateo Salazar | ✅ Mateo Salazar | ✅ Mateo Salazar | 0.91 | 1.0000 | 0.409,0.353,0.110,0.009 | 0.409,0.353,0.111,0.010 | 🟡 |
| has_signature | True | ✅ True | ❌ Sí | 0.86 | 0.9900 | 0.096,0.844,0.277,0.042 | 0.096,0.845,0.275,0.041 | 🟡 |
| statement_date | 2026-09-08 | ✅ 2026-09-08 | ✅ 2026-09-08 | 0.73 | 0.9900 | 0.333,0.180,0.205,0.012 | 0.333,0.180,0.205,0.012 | ✅ |
