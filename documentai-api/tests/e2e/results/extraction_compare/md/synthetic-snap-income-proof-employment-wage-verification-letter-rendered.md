# synthetic-snap-income-proof-employment-wage-verification-letter-rendered.png


_Last run: 2026-10-28 20:04 UTC_


## Durations

- bda: 21.34s extraction
- ocr-mapping: 1.782s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00010998
- us.amazon.nova-pro-v1:0: $0.01176880
- bda: $0.04000000
- analyze_document_layout: $0.00400000
- **total: $0.05587878**

_By Extraction Method_
- shared (preclassification): $0.00894998
- ocr-mapping extraction: $0.00692880
- primary (bda): $0.04000000
- **total: $0.05587878**


## Accuracy

_By Extracted Data_
- BDA: 6/7 (86%) equivalent match, 6/7 (86%) close, 1 miss
- OCR Mapping: 6/7 (86%) equivalent match, 6/7 (86%) close, 1 miss

_By Bounding Box_
- BDA: 0/7 exact, 7 miss
- OCR Mapping: 2/7 exact, 5 miss


## Field Comparison
| Field | Expected | BDA Value | OCR / LLM Value | BDA Conf | OCR / LLM Conf | Expected Bounding Box | BDA Bounding Box | OCR / LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| employee_name | Luis Mendoza | ✅ Luis Mendoza | ✅ Luis Mendoza | 0.88 | 1.0000 | 0.120,0.291,0.118,0.011 | ❌ 0.102,0.351,0.125,0.016 | ✅ 0.119,0.291,0.120,0.012 |
| employer_name | Harbor Home Care Services | ✅ Harbor Home Care Services | ✅ Harbor Home Care Services | 0.93 | 1.0000 | 0.121,0.863,0.209,0.011 | ❌ 0.164,0.056,0.330,0.036 | ❌ 0.179,0.064,0.455,0.028 |
| employment_end_date | - | - | - | 0.93 | - | - | - | - |
| employment_start_date | August 12, 2024 | ✅ August 12, 2024 | ❌ 2024-08-12 | 0.80 | 1.0000 | 0.121,0.466,0.390,0.015 | ❌ 0.363,0.580,0.150,0.020 | ❌ 0.368,0.466,0.143,0.015 |
| issuer_name | Dana Whitfield | ✅ Dana Whitfield | ✅ Dana Whitfield | 0.94 | 1.0000 | 0.121,0.820,0.113,0.011 | ❌ 0.099,0.966,0.236,0.034 | ❌ 0.117,0.762,0.225,0.032 |
| issuer_title | Human Resources Manager | ❌ - | ✅ Human Resources Manager | 0.91 | 1.0000 | 0.121,0.842,0.207,0.013 | ❌ - | ✅ 0.121,0.841,0.209,0.014 |
| job_title | Home Health Aide | ✅ Home Health Aide | ✅ Home Health Aide | 0.89 | 1.0000 | 0.121,0.466,0.390,0.015 | ❌ 0.143,0.580,0.165,0.016 | ❌ 0.158,0.466,0.157,0.012 |
| salary_or_wage | $19.00 per hour | ✅ $19.00 per hour | ✅ $19.00 per hour | 0.27 | 1.0000 | 0.121,0.503,0.526,0.015 | ❌ 0.513,0.629,0.142,0.020 | ❌ 0.410,0.503,0.238,0.016 |
