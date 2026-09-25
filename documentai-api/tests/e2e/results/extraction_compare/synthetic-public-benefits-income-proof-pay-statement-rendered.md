_Run: 2026-09-25 19:30 UTC_


## synthetic-public-benefits-income-proof-pay-statement-rendered.png

**Durations**

- bda: 32.14s extraction
- llm: 12.034s extraction

| Field | Expected | BDA Value | LLM (via Textract) Value | BDA Conf | LLM Conf | BDA Geometry | LLM Geometry | Geo Match |
|---|---|---|---|---|---|---|---|---|
| CityTaxes.ItemDescription | - | - | - | - | N/A | - | - |  |
| CityTaxes.Period | - | - | - | - | N/A | - | - |  |
| CityTaxes.YTD | - | - | - | - | N/A | - | - |  |
| CompanyAddress.City | - | Baltimore | Baltimore | 0.93 | N/A | 0.067,0.093,0.077,0.015 | - | ❌ |
| CompanyAddress.Line1 | - | 2458 Harford Rd | 2458 Harford Rd | 0.95 | 1.0000 | 0.067,0.072,0.125,0.012 | 0.067,0.072,0.125,0.012 | ✅ |
| CompanyAddress.Line2 | - | - | - | 0.94 | N/A | - | - |  |
| CompanyAddress.State | - | MD | MD | 0.93 | 1.0000 | 0.152,0.093,0.027,0.013 | 0.152,0.093,0.027,0.013 | ✅ |
| CompanyAddress.ZipCode | - | 21218 | 21218 | 0.93 | 1.0000 | 0.185,0.093,0.047,0.013 | 0.185,0.093,0.047,0.013 | ✅ |
| CurrentGrossPay | - | 1505.66 | 1505.66 | 0.93 | 1.0000 | 0.673,0.512,0.072,0.014 | 0.673,0.512,0.072,0.014 | ✅ |
| CurrentNetPay | - | 1148.22 | 1148.22 | 0.91 | 1.0000 | 0.341,0.804,0.103,0.019 | 0.341,0.804,0.103,0.018 | 🟡 |
| CurrentTotalDeductions | - | 457.44 | 457.44 | 0.95 | 1.0000 | 0.463,0.752,0.058,0.014 | 0.463,0.753,0.058,0.014 | 🟡 |
| EmployeeAddress.City | - | Baltimore | Baltimore | 0.94 | N/A | 0.220,0.215,0.070,0.013 | - | ❌ |
| EmployeeAddress.Line1 | - | 1824 E Lafayette Ave | 1824 E Lafayette Ave | 0.94 | 1.0000 | 0.221,0.193,0.146,0.014 | 0.221,0.193,0.146,0.014 | ✅ |
| EmployeeAddress.Line2 | - | - | - | 0.94 | N/A | - | - |  |
| EmployeeAddress.State | - | MD | MD | 0.94 | 1.0000 | 0.296,0.215,0.025,0.012 | 0.152,0.093,0.027,0.013 | ❌ |
| EmployeeAddress.ZipCode | - | 21213 | 21213 | 0.94 | 1.0000 | 0.326,0.215,0.042,0.012 | 0.326,0.215,0.042,0.012 | ✅ |
| EmployeeName.FirstName | - | Jasmine | Jasmine | 0.92 | 1.0000 | 0.219,0.170,0.057,0.011 | 0.219,0.170,0.057,0.011 | ✅ |
| EmployeeName.LastName | - | Carter | Carter | 0.91 | 1.0000 | 0.282,0.170,0.043,0.012 | 0.281,0.170,0.043,0.012 | 🟡 |
| EmployeeName.MiddleName | - | - | - | 0.93 | N/A | - | - |  |
| EmployeeName.SuffixName | - | - | - | 0.93 | N/A | - | - |  |
| EmployeeNumber | - | 10482 | 10482 | 0.94 | 1.0000 | 0.220,0.243,0.042,0.012 | 0.220,0.243,0.042,0.012 | ✅ |
| FederalFilingStatus | - | Married | Married | 0.65 | 1.0000 | 0.813,0.611,0.049,0.010 | 0.813,0.611,0.049,0.011 | 🟡 |
| FederalTaxes.ItemDescription | - | - | Federal Income Tax | - | 1.0000 | - | 0.069,0.611,0.129,0.012 | ❌ |
| FederalTaxes.Period | - | - | 186.11 | - | 1.0000 | - | 0.465,0.610,0.053,0.013 | ❌ |
| FederalTaxes.YTD | - | - | 2287.59 | - | 1.0000 | - | 0.628,0.610,0.069,0.014 | ❌ |
| HolidayHourlyRate | - | - | - | 0.95 | N/A | - | - |  |
| PayDate | - | 2026-04-17 | 04/17/2026 | 0.64 | 1.0000 | 0.739,0.094,0.087,0.013 | 0.739,0.094,0.088,0.013 | 🟡 |
| PayPeriodEndDate | - | 2026-04-15 | 04/15/2026 | 0.71 | 1.0000 | 0.852,0.070,0.086,0.013 | 0.852,0.070,0.086,0.013 | ✅ |
| PayPeriodStartDate | - | 2026-04-01 | 04/01/2026 | 0.74 | 1.0000 | 0.739,0.070,0.087,0.013 | 0.739,0.070,0.087,0.013 | ✅ |
| PayrollNumber | - | - | - | 0.95 | N/A | - | - |  |
| RegularHourlyRate | - | 18.25 | 18.25 | 0.94 | 1.0000 | 0.219,0.291,0.048,0.014 | 0.219,0.291,0.048,0.014 | ✅ |
| StateFilingStatus | - | Married | Married | 0.10 | 1.0000 | 0.813,0.611,0.049,0.011 | 0.813,0.611,0.049,0.011 | ✅ |
| StateTaxes.ItemDescription | - | - | Maryland State Tax | - | 1.0000 | - | 0.069,0.639,0.134,0.014 | ❌ |
| StateTaxes.Period | - | - | 72.78 | - | 1.0000 | - | 0.473,0.638,0.047,0.014 | ❌ |
| StateTaxes.YTD | - | - | 883.44 | - | 1.0000 | - | 0.641,0.638,0.056,0.013 | ❌ |
| YTDCityTax | - | - | - | 0.95 | N/A | - | - |  |
| YTDFederalTax | - | 2287.59 | 2287.59 | 0.94 | 1.0000 | 0.628,0.610,0.068,0.014 | 0.628,0.610,0.069,0.014 | 🟡 |
| YTDGrossPay | - | 18511.2 | 18511.20 | 0.96 | 1.0000 | 0.828,0.512,0.080,0.014 | 0.828,0.512,0.081,0.014 | 🟡 |
| YTDNetPay | - | 12921.89 | 12921.89 | 0.93 | 1.0000 | 0.662,0.902,0.087,0.015 | 0.662,0.902,0.086,0.015 | 🟡 |
| YTDStateTax | - | 883.44 | 883.44 | 0.91 | 1.0000 | 0.641,0.638,0.056,0.013 | 0.641,0.638,0.056,0.013 | ✅ |
| YTDTotalDeductions | - | 5589.31 | 5589.31 | 0.95 | 1.0000 | 0.626,0.752,0.070,0.014 | 0.626,0.753,0.070,0.014 | 🟡 |
| are_field_names_sufficient | - | True | - | 0.47 | N/A | - | - |  |
| currency | - | USD | USD | 0.93 | N/A | - | - |  |
| is_gross_pay_valid | - | True | - | 0.90 | N/A | 0.218,0.902,0.086,0.015 | - | ❌ |
| is_ytd_gross_pay_highest | - | True | - | 0.90 | N/A | 0.218,0.902,0.086,0.015 | - | ❌ |
