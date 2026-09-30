# synthetic-public-benefits-income-proof-pay-statement-rendered.png


_Run: 2026-09-30 02:19 UTC_


## Durations

- bda: 26.41s extraction
- ocr-mapping: 11.352s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00011022
- us.amazon.nova-pro-v1:0: $0.02352800
- bda: $0.04000000
- **total: $0.06363822**

_By Extraction Method_
- shared (preclassification): $0.00890542
- ocr-mapping extraction: $0.01473280
- primary (bda): $0.04000000
- **total: $0.06363822**


## Accuracy

_By Extracted Data_
- BDA: 77% equivalent, 77% close, 23% misses
- OCR Mapping: 89% equivalent, 89% close, 11% misses

_By Geometry_
- BDA: 5/18 exact, 13 miss
- OCR Mapping: 18/18 exact, 0 miss


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | Expected Geo | BDA Geometry | LLM Geometry |
|---|---|---|---|---|---|---|---|---|
| CityTaxes.ItemDescription | - | - | - | - | N/A | - | - | - |
| CityTaxes.Period | - | - | - | - | N/A | - | - | - |
| CityTaxes.YTD | - | - | - | - | N/A | - | - | - |
| CompanyAddress.City | Baltimore | ✅ Baltimore | ✅ Baltimore | 0.93 | N/A | - | 0.512,0.147,0.077,0.016 | - |
| CompanyAddress.Line1 | 2458 Harford Rd | ✅ 2458 Harford Rd | ✅ 2458 Harford Rd | 0.95 | 1.0000 | - | 0.511,0.121,0.129,0.014 | 0.067,0.072,0.125,0.012 |
| CompanyAddress.Line2 | - | - | - | 0.93 | N/A | - | - | - |
| CompanyAddress.State | MD | ✅ MD | ✅ MD | 0.93 | 1.0000 | - | 0.596,0.147,0.027,0.014 | 0.152,0.093,0.027,0.013 |
| CompanyAddress.ZipCode | 21218 | ✅ 21218 | ✅ 21218 | 0.93 | 1.0000 | - | 0.629,0.147,0.047,0.014 | 0.185,0.093,0.047,0.013 |
| CurrentGrossPay | 1505.66 | ✅ 1505.66 | ✅ 1505.66 | 0.92 | 1.0000 | 0.673,0.512,0.072,0.013 | ❌ 0.684,0.487,0.076,0.017 | ✅ 0.673,0.512,0.072,0.014 |
| CurrentNetPay | 1148.22 | ✅ 1148.22 | ✅ 1148.22 | 0.89 | 1.0000 | 0.341,0.804,0.102,0.018 | ✅ 0.336,0.824,0.108,0.022 | ✅ 0.341,0.804,0.103,0.018 |
| CurrentTotalDeductions | 457.44 | ✅ 457.44 | ✅ 457.44 | 0.94 | 1.0000 | 0.462,0.753,0.057,0.013 | ✅ 0.463,0.765,0.060,0.016 | ✅ 0.463,0.753,0.058,0.014 |
| EmployeeAddress.City | Baltimore | ✅ Baltimore | ✅ Baltimore | 0.93 | N/A | - | 0.209,0.143,0.073,0.015 | - |
| EmployeeAddress.Line1 | 1824 E Lafayette Ave | ✅ 1824 E Lafayette Ave | ✅ 1824 E Lafayette Ave | 0.94 | 1.0000 | - | 0.209,0.118,0.153,0.017 | 0.221,0.193,0.146,0.014 |
| EmployeeAddress.Line2 | - | - | - | 0.93 | N/A | - | - | - |
| EmployeeAddress.State | MD | ✅ MD | ✅ MD | 0.93 | 1.0000 | - | 0.288,0.143,0.026,0.013 | 0.152,0.093,0.027,0.013 |
| EmployeeAddress.ZipCode | 21213 | ✅ 21213 | ✅ 21213 | 0.93 | 1.0000 | 0.325,0.215,0.042,0.011 | ❌ 0.319,0.143,0.044,0.014 | ✅ 0.326,0.215,0.042,0.012 |
| EmployeeName.FirstName | Jasmine | ✅ Jasmine | ✅ Jasmine | 0.91 | 1.0000 | 0.219,0.170,0.056,0.011 | ❌ 0.208,0.091,0.059,0.013 | ✅ 0.219,0.170,0.057,0.011 |
| EmployeeName.LastName | Carter | ✅ Carter | ✅ Carter | 0.89 | 1.0000 | 0.281,0.170,0.042,0.011 | ❌ 0.273,0.091,0.044,0.013 | ✅ 0.281,0.170,0.043,0.012 |
| EmployeeName.MiddleName | - | - | - | 0.91 | N/A | - | - | - |
| EmployeeName.SuffixName | - | - | - | 0.93 | N/A | - | - | - |
| EmployeeNumber | 10482 | ✅ 10482 | ✅ 10482 | 0.93 | 1.0000 | 0.220,0.243,0.041,0.011 | ❌ 0.209,0.176,0.044,0.013 | ✅ 0.220,0.243,0.042,0.012 |
| FederalFilingStatus | Married | ✅ Married | ✅ Married | 0.30 | 1.0000 | - | 0.832,0.602,0.051,0.012 | 0.813,0.611,0.049,0.011 |
| FederalTaxes.ItemDescription | Federal Income Tax | ❌ - | ✅ Federal Income Tax | - | 1.0000 | - | - | 0.069,0.611,0.129,0.012 |
| FederalTaxes.Period | 186.11 | ❌ - | ✅ 186.11 | - | 1.0000 | 0.465,0.610,0.052,0.013 | ❌ - | ✅ 0.465,0.610,0.053,0.013 |
| FederalTaxes.YTD | 2287.59 | ❌ - | ✅ 2287.59 | - | 1.0000 | 0.627,0.610,0.068,0.013 | ❌ - | ✅ 0.628,0.610,0.069,0.014 |
| HolidayHourlyRate | - | - | - | 0.94 | N/A | - | - | - |
| PayDate | 2026-04-17 | ✅ 2026-04-17 | ✅ 2026-04-17 | 0.68 | 1.0000 | 0.739,0.094,0.087,0.013 | ❌ 0.754,0.004,0.092,0.015 | ✅ 0.739,0.094,0.088,0.013 |
| PayPeriodEndDate | 2026-04-15 | ❌ 2026-04-17 | ✅ 2026-04-15 | 0.02 | 1.0000 | 0.851,0.070,0.085,0.012 | ❌ - | ✅ 0.852,0.070,0.086,0.013 |
| PayPeriodStartDate | 2026-04-01 | ❌ - | ✅ 2026-04-01 | 0.02 | 1.0000 | 0.739,0.070,0.087,0.012 | ❌ - | ✅ 0.739,0.070,0.087,0.013 |
| PayrollNumber | - | - | - | 0.94 | N/A | - | - | - |
| RegularHourlyRate | 18.25 | ✅ 18.25 | ✅ 18.25 | 0.93 | 1.0000 | - | 0.208,0.232,0.050,0.016 | 0.219,0.291,0.048,0.014 |
| StateFilingStatus | Married | ✅ Married | ✅ Married | 0.07 | 1.0000 | - | 0.832,0.601,0.051,0.013 | 0.813,0.611,0.049,0.011 |
| StateTaxes.ItemDescription | Maryland State Tax | ❌ - | ✅ Maryland State Tax | - | 1.0000 | - | - | 0.069,0.639,0.134,0.014 |
| StateTaxes.Period | 72.78 | ❌ - | ✅ 72.78 | - | 1.0000 | 0.473,0.638,0.045,0.013 | ❌ - | ✅ 0.473,0.638,0.047,0.014 |
| StateTaxes.YTD | 883.44 | ❌ - | ✅ 883.44 | - | 1.0000 | 0.641,0.638,0.054,0.013 | ❌ - | ✅ 0.641,0.638,0.056,0.013 |
| YTDCityTax | - | - | - | 0.94 | N/A | - | - | - |
| YTDFederalTax | 2287.59 | ✅ 2287.59 | ✅ 2287.59 | 0.94 | 1.0000 | 0.627,0.610,0.068,0.013 | ✅ 0.637,0.600,0.072,0.016 | ✅ 0.628,0.610,0.069,0.014 |
| YTDGrossPay | 18511.20 | ✅ 18511.2 | ✅ 18511.20 | 0.96 | 1.0000 | - | 0.847,0.487,0.084,0.016 | 0.828,0.512,0.081,0.014 |
| YTDNetPay | 12921.89 | ✅ 12921.89 | ✅ 12921.89 | 0.93 | 1.0000 | 0.662,0.902,0.085,0.015 | ❌ 0.673,0.938,0.090,0.018 | ✅ 0.662,0.902,0.086,0.015 |
| YTDStateTax | 883.44 | ✅ 883.44 | ✅ 883.44 | 0.91 | 1.0000 | 0.641,0.638,0.054,0.013 | ✅ 0.651,0.633,0.059,0.015 | ✅ 0.641,0.638,0.056,0.013 |
| YTDTotalDeductions | 5589.31 | ✅ 5589.31 | ✅ 5589.31 | 0.94 | 1.0000 | 0.626,0.752,0.068,0.014 | ✅ 0.635,0.765,0.072,0.016 | ✅ 0.626,0.753,0.070,0.014 |
| are_field_names_sufficient | True | ✅ True | ❌ - | 0.44 | N/A | - | - | - |
| currency | USD | ✅ USD | ❌ - | 0.91 | N/A | - | - | - |
| is_gross_pay_valid | True | ✅ True | ❌ - | 0.89 | N/A | - | 0.206,0.938,0.090,0.017 | - |
| is_ytd_gross_pay_highest | True | ✅ True | ❌ - | 0.89 | N/A | - | 0.206,0.938,0.090,0.017 | - |
