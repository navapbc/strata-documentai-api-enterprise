# Extraction Compare Results

_Run: 2026-09-25 15:10 UTC_


## synthetic-public-benefits-identity-proof-state-photo-id.jpg

**Durations**

- llm: 11.842s extraction
- textract: 2.32s extraction

| Field | Expected | TEXTRACT Value | LLM (via Textract) Value | TEXTRACT Conf | LLM Conf | TEXTRACT Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| ADDRESS_DETAILS.CITY | LAS VEGAS | ✅ LAS VEGAS | ✅ LAS VEGAS | 0.97 | N/A | - | 0.405,0.501,0.096,0.027 | ❌ |
| ADDRESS_DETAILS.STATE | NV | ✅ NV | ✅ NV | 0.98 | 1.0000 | 0.505,0.498,0.024,0.021 | 0.506,0.499,0.023,0.020 | 🟡 |
| ADDRESS_DETAILS.STREET_ADDRESS | 4821 DESERT BLOOM AVE | ✅ 4821 DESERT BLOOM AVE | ✅ 4821 DESERT BLOOM AVE | 0.97 | 1.0000 | 0.402,0.458,0.209,0.041 | 0.403,0.461,0.208,0.038 | 🟡 |
| ADDRESS_DETAILS.ZIP_CODE | 89146 | ✅ 89146 | ✅ 89146 | 0.98 | 1.0000 | 0.646,0.588,0.057,0.028 | 0.534,0.494,0.049,0.023 | ❌ |
| CLASS | D | ✅ D | ✅ D | 0.98 | 0.9700 | 0.353,0.730,0.012,0.020 | 0.355,0.731,0.011,0.019 | 🟡 |
| COUNTY | - | - | - | 0.99 | - | - | - |  |
| DATE_OF_BIRTH | 1996-05-14 | ✅ 1996-05-14 | ✅ 1996-05-14 | 0.96 | 1.0000 | 0.638,0.460,0.105,0.034 | 0.639,0.462,0.104,0.032 | 🟡 |
| DATE_OF_ISSUE | 2021-06-18 | ✅ 2021-06-18 | ✅ 2021-06-18 | 0.98 | 1.0000 | 0.409,0.606,0.090,0.031 | 0.410,0.608,0.089,0.030 | 🟡 |
| ENDORSEMENTS | - | - | - | 0.98 | - | - | - |  |
| EXPIRATION_DATE | 2029-06-18 | ✅ 2029-06-18 | ✅ 2029-06-18 | 0.97 | 1.0000 | 0.536,0.594,0.091,0.031 | 0.537,0.596,0.090,0.030 | 🟡 |
| ID_NUMBER | DEMO-4821-55 | ❌ DEMO482155 | ✅ DEMO-4821-55 | 0.96 | 0.9800 | 0.633,0.360,0.144,0.038 | 0.635,0.362,0.142,0.034 | 🟡 |
| NAME_DETAILS.FIRST_NAME | ELENA | ✅ ELENA | ✅ ELENA | 0.94 | 1.0000 | 0.398,0.378,0.070,0.030 | 0.399,0.380,0.069,0.028 | 🟡 |
| NAME_DETAILS.LAST_NAME | MARTINEZ | ✅ MARTINEZ | ✅ MARTINEZ | 0.62 | 1.0000 | 0.471,0.369,0.108,0.034 | 0.473,0.370,0.107,0.031 | 🟡 |
| NAME_DETAILS.MIDDLE_NAME | - | ❌ MARTINEZ | - | 0.98 | - | 0.471,0.369,0.108,0.034 | - | ❌ |
| NAME_DETAILS.SUFFIX | - | - | - | 0.99 | - | - | - |  |
| PERSONAL_DETAILS.EYE_COLOR | - | - | - | - | - | - | - |  |
| PERSONAL_DETAILS.HAIR_COLOR | - | - | - | - | - | - | - |  |
| PERSONAL_DETAILS.HEIGHT | - | - | - | - | - | - | - |  |
| PERSONAL_DETAILS.SEX | F | ✅ F | ✅ F | 1.00 | 1.0000 | 0.761,0.458,0.014,0.024 | 0.763,0.460,0.013,0.022 | 🟡 |
| PERSONAL_DETAILS.WEIGHT | - | - | - | - | - | - | - |  |
| RESTRICTIONS | NONE | ✅ NONE | ✅ NONE | 0.98 | 1.0000 | 0.431,0.718,0.046,0.025 | 0.433,0.721,0.045,0.022 | 🟡 |
| STATE_NAME | - | - | - | 0.13 | - | - | - |  |


## synthetic-public-benefits-income-proof-pay-stub.jpg

**Durations**

- bda: 24.02s extraction
- llm: 18.697s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| CityTaxes.ItemDescription | - | - | - | - | N/A | - | - |  |
| CityTaxes.Period | - | - | - | - | N/A | - | - |  |
| CityTaxes.YTD | - | - | - | - | N/A | - | - |  |
| CompanyAddress.City | Hartford | ✅ Hartford | ✅ Hartford | 0.94 | N/A | 0.137,0.289,0.042,0.017 | - | ❌ |
| CompanyAddress.Line1 | 1234 Community Way | ✅ 1234 Community Way | ✅ 1234 Community Way | 0.95 | 1.0000 | 0.137,0.261,0.104,0.024 | 0.137,0.261,0.104,0.021 | 🟡 |
| CompanyAddress.Line2 | - | - | - | 0.95 | N/A | - | - |  |
| CompanyAddress.State | ST | ✅ ST | ✅ ST | 0.92 | 1.0000 | 0.182,0.288,0.013,0.012 | 0.182,0.288,0.013,0.012 | ✅ |
| CompanyAddress.ZipCode | 06103 | ✅ 06103 | ✅ 06103 | 0.94 | 1.0000 | 0.197,0.285,0.029,0.014 | 0.197,0.285,0.029,0.014 | ✅ |
| CurrentGrossPay | 1350.00 | 🟡 1350 | ✅ 1350.00 | 0.95 | 1.0000 | 0.407,0.619,0.048,0.020 | 0.400,0.376,0.039,0.016 | ❌ |
| CurrentNetPay | 1037.56 | ✅ 1037.56 | ✅ 1037.56 | 0.94 | 1.0000 | 0.737,0.751,0.041,0.018 | 0.755,0.579,0.047,0.020 | ❌ |
| CurrentTotalDeductions | 312.44 | ✅ 312.44 | ✅ 312.44 | 0.45 | 1.0000 | 0.765,0.533,0.031,0.015 | 0.765,0.532,0.031,0.015 | 🟡 |
| EmployeeAddress.City | - | - | - | 0.93 | N/A | - | - |  |
| EmployeeAddress.Line1 | - | - | - | 0.94 | N/A | - | - |  |
| EmployeeAddress.Line2 | - | - | - | 0.95 | N/A | - | - |  |
| EmployeeAddress.State | - | - | - | 0.92 | N/A | - | - |  |
| EmployeeAddress.ZipCode | - | - | - | 0.94 | N/A | - | - |  |
| EmployeeName.FirstName | Elena | ✅ Elena | ✅ Elena | 0.95 | 1.0000 | 0.471,0.209,0.025,0.013 | 0.471,0.209,0.025,0.013 | ✅ |
| EmployeeName.LastName | Martinez | ✅ Martinez | ✅ Martinez | 0.90 | 1.0000 | 0.499,0.205,0.038,0.014 | 0.499,0.205,0.038,0.014 | ✅ |
| EmployeeName.MiddleName | - | - | - | 0.93 | N/A | - | - |  |
| EmployeeName.SuffixName | - | - | - | 0.94 | N/A | - | - |  |
| EmployeeNumber | EMP-78245 | ✅ EMP-78245 | ✅ EMP-78245 | 0.90 | 1.0000 | 0.473,0.228,0.053,0.016 | 0.473,0.228,0.052,0.016 | 🟡 |
| FederalFilingStatus | - | - | - | 0.94 | N/A | - | - |  |
| FederalTaxes.ItemDescription | Federal Income Tax | ❌ - | ✅ Federal Income Tax | - | 1.0000 | - | 0.533,0.357,0.072,0.017 | ❌ |
| FederalTaxes.Period | 152.10 | ❌ - | ✅ 152.10 | - | 1.0000 | - | 0.741,0.340,0.031,0.013 | ❌ |
| FederalTaxes.YTD | 1064.70 | ❌ - | ✅ 1064.70 | - | 1.0000 | - | 0.820,0.332,0.036,0.015 | ❌ |
| HolidayHourlyRate | - | - | - | 0.95 | N/A | - | - |  |
| PayDate | 2026-04-03 | ✅ 2026-04-03 | 🟡 04/03/2026 | 0.80 | 1.0000 | 0.709,0.201,0.044,0.014 | 0.709,0.201,0.044,0.014 | ✅ |
| PayPeriodEndDate | 2026-03-31 | ✅ 2026-03-31 | 🟡 03/31/2026 | 0.89 | 0.8700 | 0.759,0.223,0.041,0.013 | 0.759,0.224,0.040,0.013 | 🟡 |
| PayPeriodStartDate | 2026-03-16 | ✅ 2026-03-16 | 🟡 03/16/2026 | 0.88 | 0.8700 | 0.712,0.227,0.046,0.013 | 0.712,0.223,0.087,0.018 | ❌ |
| PayrollNumber | - | - | - | 0.95 | N/A | - | - |  |
| RegularHourlyRate | 16.88 | ✅ 16.88 | ✅ 16.88 | 0.95 | 1.0000 | 0.325,0.385,0.028,0.013 | 0.325,0.385,0.028,0.013 | ✅ |
| StateFilingStatus | - | - | - | 0.94 | N/A | - | - |  |
| StateTaxes.ItemDescription | State Income Tax | ❌ - | ✅ State Income Tax | - | 1.0000 | - | 0.535,0.382,0.065,0.016 | ❌ |
| StateTaxes.Period | 59.48 | ❌ - | ✅ 59.48 | - | 1.0000 | - | 0.748,0.364,0.026,0.013 | ❌ |
| StateTaxes.YTD | 416.36 | ❌ - | ✅ 416.36 | - | 1.0000 | - | 0.829,0.355,0.031,0.014 | ❌ |
| YTDCityTax | - | - | - | 0.95 | N/A | - | - |  |
| YTDFederalTax | 1064.70 | 🟡 1064.7 | ✅ 1064.70 | 0.96 | 1.0000 | 0.819,0.332,0.036,0.015 | 0.820,0.332,0.036,0.015 | 🟡 |
| YTDGrossPay | 9450.00 | 🟡 9450 | ✅ 9450.00 | 0.96 | 1.0000 | 0.481,0.610,0.047,0.020 | 0.470,0.370,0.038,0.015 | ❌ |
| YTDNetPay | 6562.92 | ✅ 6562.92 | ✅ 6562.92 | 0.95 | 1.0000 | 0.841,0.568,0.046,0.019 | 0.841,0.568,0.046,0.020 | 🟡 |
| YTDStateTax | 416.36 | ✅ 416.36 | ✅ 416.36 | 0.95 | 1.0000 | 0.829,0.355,0.031,0.014 | 0.829,0.355,0.031,0.014 | ✅ |
| YTDTotalDeductions | 2887.08 | ✅ 2887.08 | ✅ 2887.08 | 0.58 | 1.0000 | 0.844,0.523,0.037,0.016 | 0.844,0.523,0.037,0.016 | ✅ |
| are_field_names_sufficient | True | ✅ True | ❌ - | 0.07 | N/A | - | - |  |
| currency | USD | ✅ USD | ✅ USD | 0.92 | N/A | 0.182,0.288,0.013,0.012 | - | ❌ |
| is_gross_pay_valid | True | ✅ True | ❌ - | 0.92 | N/A | 0.481,0.610,0.047,0.020 | - | ❌ |
| is_ytd_gross_pay_highest | True | ✅ True | ❌ - | 0.92 | N/A | 0.481,0.610,0.047,0.020 | - | ❌ |


## synthetic-snap-income-proof-employment-wage-verification-letter-rendered.png

**Durations**

- bda: 23.78s extraction
- llm: 1.416s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| employee_name | Luis Mendoza | ✅ Luis Mendoza | ✅ Luis Mendoza | 0.88 | 1.0000 | 0.105,0.349,0.124,0.015 | 0.119,0.291,0.120,0.012 | ❌ |
| employer_name | Harbor Home Care Services | ✅ Harbor Home Care Services | ✅ Harbor Home Care Services | 0.93 | 1.0000 | 0.167,0.072,0.472,0.034 | 0.179,0.064,0.455,0.028 | ❌ |
| employment_end_date | - | - | - | 0.93 | - | - | - |  |
| employment_start_date | August 12, 2024 | ✅ August 12, 2024 | ✅ August 12, 2024 | 0.80 | 1.0000 | 0.364,0.563,0.148,0.019 | 0.368,0.466,0.143,0.015 | ❌ |
| issuer_name | Dana Whitfield | ✅ Dana Whitfield | ✅ Dana Whitfield | 0.94 | 1.0000 | 0.100,0.926,0.238,0.040 | 0.117,0.762,0.225,0.032 | ❌ |
| issuer_title | Human Resources Manager | ❌ - | ✅ Human Resources Manager | 0.91 | 1.0000 | - | 0.121,0.841,0.209,0.014 | ❌ |
| job_title | Home Health Aide | ✅ Home Health Aide | ✅ Home Health Aide | 0.88 | 1.0000 | 0.146,0.563,0.163,0.015 | 0.158,0.466,0.157,0.012 | ❌ |
| salary_or_wage | $19.00 per hour | ✅ $19.00 per hour | ✅ $19.00 per hour | 0.32 | 1.0000 | 0.513,0.609,0.141,0.019 | 0.410,0.503,0.238,0.016 | ❌ |
