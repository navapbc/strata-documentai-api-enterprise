# synthetic-snap-income-proof-employment-wage-verification-letter-rendered.png


_Run: 2026-10-01 01:41 UTC_


## Durations

- bda: 17.8s extraction
- ocr-mapping: 1.637s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00010998
- us.amazon.nova-pro-v1:0: $0.01175920
- bda: $0.04000000
- **total: $0.05186918**

_By Extraction Method_
- shared (preclassification): $0.00892758
- ocr-mapping extraction: $0.00294160
- primary (bda): $0.04000000
- **total: $0.05186918**


## Accuracy

_By Extracted Data_
- BDA: 100% equivalent, 100% close, 0% misses
- OCR Mapping: 86% equivalent, 86% close, 14% misses

_By Bounding Box_
- BDA: 2/7 exact, 5 miss
- OCR Mapping: 2/7 exact, 5 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Bounding Box | BDA Bounding Box | LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| employee_name | Luis Mendoza | ✅ Luis Mendoza | ✅ Luis Mendoza | 0.90 | 1.0000 | 0.120,0.291,0.118,0.011 | ✅ 0.119,0.291,0.120,0.012 | ✅ 0.119,0.291,0.120,0.012 |
| employer_name | Harbor Home Care Services | ✅ Harbor Home Care Services | ✅ Harbor Home Care Services | 0.94 | 1.0000 | 0.121,0.863,0.209,0.011 | ❌ 0.179,0.064,0.455,0.028 | ❌ 0.179,0.064,0.455,0.028 |
| employment_end_date | - | - | - | 0.93 | - | - | - | - |
| employment_start_date | August 12, 2024 | ✅ August 12, 2024 | ❌ 2024-08-12 | 0.81 | 1.0000 | 0.121,0.466,0.390,0.015 | ❌ 0.368,0.466,0.143,0.015 | ❌ 0.368,0.466,0.143,0.015 |
| issuer_name | Dana Whitfield | ✅ Dana Whitfield | ✅ Dana Whitfield | 0.95 | 1.0000 | 0.121,0.820,0.113,0.011 | ❌ 0.210,0.765,0.132,0.029 | ❌ 0.117,0.762,0.225,0.032 |
| issuer_title | Human Resources Manager | ✅ Human Resources Manager | ✅ Human Resources Manager | 0.92 | 1.0000 | 0.121,0.842,0.207,0.013 | ✅ 0.121,0.841,0.209,0.014 | ✅ 0.121,0.841,0.209,0.014 |
| job_title | Home Health Aide | ✅ Home Health Aide | ✅ Home Health Aide | 0.89 | 1.0000 | 0.121,0.466,0.390,0.015 | ❌ 0.158,0.465,0.157,0.012 | ❌ 0.158,0.466,0.157,0.012 |
| salary_or_wage | $19.00 per hour | ✅ $19.00 per hour | ✅ $19.00 per hour | 0.35 | 1.0000 | 0.121,0.503,0.526,0.015 | ❌ 0.512,0.503,0.136,0.016 | ❌ 0.410,0.503,0.238,0.016 |
