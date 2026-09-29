# synthetic-public-benefits-income-proof-pay-statement-photo.png


_Run: 2026-09-29 20:00 UTC_


## Durations

- bda: 25.95s extraction
- ocr-mapping: 12.078s extraction


## Cost

_By Service_
- us.amazon.nova-lite-v1:0: $0.00011394 (1791 in / 27 out)
- us.amazon.nova-pro-v1:0: $0.02361840 (23155 in / 1592 out)
- bda: $0.04000000 (1 page(s))
- **total: $0.06373234**

_By Extraction Method_
- shared (preclassification): $0.00898274
- ocr-mapping extraction: $0.01474960
- primary (bda): $0.04000000
- **total: $0.06373234**


## Accuracy
- BDA: 83% equivalent, 83% close, 17% misses
- OCR Mapping: 91% equivalent, 91% close, 9% misses


## Field Comparison
| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| CityTaxes.ItemDescription | - | - | - | - | N/A | - | - |  |
| CityTaxes.Period | - | - | - | - | N/A | - | - |  |
| CityTaxes.YTD | - | - | - | - | N/A | - | - |  |
| CompanyAddress.City | Baltimore | ✅ Baltimore | ✅ Baltimore | 0.93 | N/A | 0.164,0.132,0.066,0.013 | - | ❌ |
| CompanyAddress.Line1 | 2458 Harford Rd | ✅ 2458 Harford Rd | ✅ 2458 Harford Rd | 0.95 | 1.0000 | 0.163,0.114,0.108,0.013 | 0.163,0.114,0.108,0.012 | 🟡 |
| CompanyAddress.Line2 | - | - | - | 0.94 | N/A | - | - |  |
| CompanyAddress.State | MD | ✅ MD | ✅ MD | 0.93 | 1.0000 | 0.236,0.134,0.023,0.011 | 0.236,0.133,0.023,0.011 | 🟡 |
| CompanyAddress.ZipCode | 21218 | ✅ 21218 | ✅ 21218 | 0.93 | 1.0000 | 0.263,0.134,0.040,0.011 | 0.263,0.134,0.040,0.011 | ✅ |
| CurrentGrossPay | 1505.66 | ✅ 1505.66 | ✅ 1505.66 | 0.93 | 1.0000 | 0.674,0.493,0.063,0.012 | 0.674,0.493,0.063,0.012 | ✅ |
| CurrentNetPay | 1148.22 | ✅ 1148.22 | ✅ 1148.22 | 0.90 | 1.0000 | 0.384,0.764,0.093,0.020 | 0.384,0.764,0.093,0.019 | 🟡 |
| CurrentTotalDeductions | 457.44 | ✅ 457.44 | ✅ 457.44 | 0.95 | 1.0000 | 0.493,0.713,0.052,0.014 | 0.494,0.713,0.052,0.014 | 🟡 |
| EmployeeAddress.City | Baltimore | ✅ Baltimore | ✅ Baltimore | 0.94 | N/A | 0.292,0.238,0.057,0.012 | - | ❌ |
| EmployeeAddress.Line1 | 1824 E Lafayette Ave | ✅ 1824 E Lafayette Ave | ✅ 1824 E Lafayette Ave | 0.95 | 1.0000 | 0.293,0.219,0.118,0.013 | 0.293,0.220,0.118,0.013 | 🟡 |
| EmployeeAddress.Line2 | - | - | - | 0.93 | N/A | - | - |  |
| EmployeeAddress.State | MD | ✅ MD | ✅ MD | 0.94 | 1.0000 | 0.354,0.238,0.020,0.010 | 0.236,0.133,0.023,0.011 | ❌ |
| EmployeeAddress.ZipCode | 21213 | ✅ 21213 | ✅ 21213 | 0.94 | 1.0000 | 0.379,0.238,0.035,0.010 | 0.379,0.238,0.035,0.010 | ✅ |
| EmployeeName.FirstName | Jasmine | ✅ Jasmine | ✅ Jasmine | 0.92 | 1.0000 | 0.292,0.202,0.046,0.010 | 0.292,0.201,0.046,0.010 | 🟡 |
| EmployeeName.LastName | Carter | ✅ Carter | ✅ Carter | 0.91 | 1.0000 | 0.341,0.202,0.035,0.010 | 0.341,0.202,0.035,0.010 | ✅ |
| EmployeeName.MiddleName | - | - | - | 0.93 | N/A | - | - |  |
| EmployeeName.SuffixName | - | - | - | 0.93 | N/A | - | - |  |
| EmployeeNumber | 10482 | ✅ 10482 | ✅ 10482 | 0.94 | 1.0000 | 0.292,0.261,0.034,0.010 | 0.292,0.261,0.035,0.010 | 🟡 |
| FederalFilingStatus | Married | ✅ Married | ✅ Married | 0.70 | 1.0000 | 0.799,0.579,0.044,0.010 | 0.799,0.579,0.044,0.010 | ✅ |
| FederalTaxes.ItemDescription | Federal Income Tax | ❌ - | ✅ Federal Income Tax | - | 1.0000 | - | 0.143,0.584,0.116,0.011 | ❌ |
| FederalTaxes.Period | 186.11 | ❌ - | ✅ 186.11 | - | 1.0000 | - | 0.495,0.581,0.046,0.012 | ❌ |
| FederalTaxes.YTD | 2287.59 | ❌ - | ✅ 2287.59 | - | 1.0000 | - | 0.637,0.580,0.060,0.012 | ❌ |
| HolidayHourlyRate | - | - | - | 0.95 | N/A | - | - |  |
| PayDate | 2026-04-17 | ✅ 2026-04-17 | ✅ 2026-04-17 | 0.67 | 1.0000 | 0.704,0.140,0.072,0.013 | 0.704,0.140,0.072,0.013 | ✅ |
| PayPeriodEndDate | 2026-04-15 | ✅ 2026-04-15 | ✅ 2026-04-15 | 0.77 | 1.0000 | 0.796,0.122,0.070,0.012 | 0.796,0.122,0.070,0.012 | ✅ |
| PayPeriodStartDate | 2026-04-01 | ✅ 2026-04-01 | ✅ 2026-04-01 | 0.78 | 1.0000 | 0.705,0.121,0.072,0.013 | 0.705,0.121,0.072,0.013 | ✅ |
| PayrollNumber | - | - | - | 0.95 | N/A | - | - |  |
| RegularHourlyRate | 18.25 | ✅ 18.25 | ✅ 18.25 | 0.94 | 1.0000 | 0.290,0.302,0.039,0.012 | 0.290,0.302,0.039,0.012 | ✅ |
| StateFilingStatus | Married | ✅ Married | ✅ Married | 0.12 | 1.0000 | 0.799,0.579,0.044,0.010 | 0.799,0.579,0.044,0.010 | ✅ |
| StateTaxes.ItemDescription | Maryland State Tax | ❌ - | ✅ Maryland State Tax | - | 1.0000 | - | 0.142,0.610,0.120,0.014 | ❌ |
| StateTaxes.Period | 72.78 | ❌ - | ✅ 72.78 | - | 1.0000 | - | 0.502,0.606,0.041,0.012 | ❌ |
| StateTaxes.YTD | 883.44 | ❌ - | ✅ 883.44 | - | 1.0000 | - | 0.649,0.604,0.049,0.013 | ❌ |
| YTDCityTax | - | - | - | 0.95 | N/A | - | - |  |
| YTDFederalTax | 2287.59 | ✅ 2287.59 | ✅ 2287.59 | 0.94 | 1.0000 | 0.636,0.579,0.060,0.013 | 0.637,0.580,0.060,0.012 | 🟡 |
| YTDGrossPay | 18511.20 | ✅ 18511.2 | ✅ 18511.20 | 0.96 | 1.0000 | 0.810,0.492,0.071,0.012 | 0.809,0.492,0.071,0.012 | 🟡 |
| YTDNetPay | 12921.89 | ✅ 12921.89 | ✅ 12921.89 | 0.93 | 1.0000 | 0.678,0.855,0.078,0.017 | 0.678,0.855,0.078,0.016 | 🟡 |
| YTDStateTax | 883.44 | ✅ 883.44 | ✅ 883.44 | 0.91 | 1.0000 | 0.649,0.604,0.049,0.012 | 0.649,0.604,0.049,0.013 | 🟡 |
| YTDTotalDeductions | 5589.31 | ✅ 5589.31 | ✅ 5589.31 | 0.95 | 1.0000 | 0.640,0.711,0.062,0.014 | 0.640,0.712,0.062,0.014 | 🟡 |
| are_field_names_sufficient | True | ✅ True | ❌ - | 0.46 | N/A | - | - |  |
| currency | USD | ✅ USD | ✅ USD | 0.92 | N/A | 0.236,0.134,0.023,0.011 | - | ❌ |
| is_gross_pay_valid | True | ✅ True | ❌ - | 0.89 | N/A | 0.269,0.863,0.080,0.017 | - | ❌ |
| is_ytd_gross_pay_highest | True | ✅ True | ❌ - | 0.90 | N/A | 0.269,0.863,0.080,0.017 | - | ❌ |
