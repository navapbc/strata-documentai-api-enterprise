# synthetic-snap-income-proof-employment-wage-verification-letter-photo.png


_Run: 2026-09-30 02:19 UTC_


## Durations

- bda: 18.84s extraction
- ocr-mapping: 1.416s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00011394
- us.amazon.nova-pro-v1:0: $0.01185520
- bda: $0.04000000
- **total: $0.05196914**

_By Extraction Method_
- shared (preclassification): $0.00902754
- ocr-mapping extraction: $0.00294160
- primary (bda): $0.04000000
- **total: $0.05196914**


## Accuracy

_By Extracted Data_
- BDA: 100% equivalent, 100% close, 0% misses
- OCR Mapping: 86% equivalent, 86% close, 14% misses

_By Geometry_
- BDA: 2/3 exact, 1 miss
- OCR Mapping: 2/3 exact, 1 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Geo | BDA Geometry | LLM Geometry |
|---|---|---|---|---|---|---|---|---|
| employee_name | Luis Mendoza | ✅ Luis Mendoza | ✅ Luis Mendoza | 0.90 | 0.9900 | 0.195,0.269,0.105,0.011 | ✅ 0.194,0.268,0.107,0.013 | ✅ 0.194,0.269,0.107,0.013 |
| employer_name | Harbor Home Care Services | ✅ Harbor Home Care Services | ✅ Harbor Home Care Services | 0.94 | 1.0000 | 0.180,0.778,0.197,0.012 | ❌ 0.252,0.085,0.387,0.039 | ❌ 0.252,0.086,0.387,0.038 |
| employment_end_date | - | - | - | 0.93 | - | - | - | - |
| employment_start_date | August 12, 2024 | ✅ August 12, 2024 | ❌ 2024-08-12 | 0.81 | 1.0000 | - | 0.413,0.423,0.124,0.014 | 0.413,0.423,0.124,0.013 |
| issuer_name | Dana Whitfield | ✅ Dana Whitfield | ✅ Dana Whitfield | 0.95 | 1.0000 | - | 0.264,0.685,0.124,0.030 | 0.178,0.685,0.210,0.029 |
| issuer_title | Human Resources Manager | ✅ Human Resources Manager | ✅ Human Resources Manager | 0.93 | 1.0000 | 0.180,0.758,0.195,0.012 | ✅ 0.179,0.755,0.197,0.020 | ✅ 0.179,0.757,0.197,0.015 |
| job_title | Home Health Aide | ✅ Home Health Aide | ✅ Home Health Aide | 0.89 | 1.0000 | - | 0.223,0.420,0.143,0.013 | 0.223,0.420,0.143,0.012 |
| salary_or_wage | $19.00 per hour | ✅ $19.00 per hour | ✅ $19.00 per hour | 0.35 | 1.0000 | - | 0.538,0.456,0.116,0.014 | 0.450,0.455,0.204,0.014 |
