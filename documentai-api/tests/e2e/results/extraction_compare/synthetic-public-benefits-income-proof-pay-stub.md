_Run: 2026-09-25 19:30 UTC_


## synthetic-public-benefits-income-proof-pay-stub.jpg

**Durations**

- bda: 24.98s extraction
- llm: 12.98s extraction

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
| CurrentTotalDeductions | 312.44 | ✅ 312.44 | ✅ 312.44 | 0.43 | 1.0000 | 0.765,0.533,0.031,0.015 | 0.765,0.532,0.031,0.015 | 🟡 |
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
| YTDTotalDeductions | 2887.08 | ✅ 2887.08 | ✅ 2887.08 | 0.57 | 1.0000 | 0.844,0.523,0.037,0.016 | 0.844,0.523,0.037,0.016 | ✅ |
| are_field_names_sufficient | True | ✅ True | ❌ - | 0.07 | N/A | - | - |  |
| currency | USD | ✅ USD | ✅ USD | 0.92 | N/A | 0.182,0.288,0.013,0.012 | - | ❌ |
| is_gross_pay_valid | True | ✅ True | ❌ - | 0.92 | N/A | 0.481,0.610,0.047,0.020 | - | ❌ |
| is_ytd_gross_pay_highest | True | ✅ True | ❌ - | 0.92 | N/A | 0.481,0.610,0.047,0.020 | - | ❌ |
