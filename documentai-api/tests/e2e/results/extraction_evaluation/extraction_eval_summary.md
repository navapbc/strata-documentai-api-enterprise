# Extraction Eval Results

_Run: 2026-09-24 03:47 UTC_


## synthetic-public-benefits-identity-proof-state-photo-id.jpg

**Durations**

- llm: 2.611s extraction
- textract: 2.68s extraction

| Field | TEXTRACT Value | Conf | LLM Value | LLM Conf |
|---|---|---|---|---|
| ADDRESS_DETAILS.CITY | LAS VEGAS | 0.97 | LAS VEGAS | 0.0000 |
| ADDRESS_DETAILS.STATE | NV | 0.98 | NV | 0.0000 |
| ADDRESS_DETAILS.STREET_ADDRESS | 4821 DESERT BLOOM AVE | 0.97 | 4821 DESERT BLOOM AVE | 0.0000 |
| ADDRESS_DETAILS.ZIP_CODE | 89146 | 0.98 | 89146 | 0.0000 |
| CLASS | D | 0.98 | D | 0.0000 |
| COUNTY | — | 0.99 | — | 0.0000 |
| DATE_OF_BIRTH | 1996-05-14 | 0.96 | 05/14/1996 | 0.0000 |
| DATE_OF_ISSUE | 2021-06-18 | 0.98 | 06/18/2021 | 0.0000 |
| ENDORSEMENTS | — | 0.98 | — | 0.0000 |
| EXPIRATION_DATE | 2029-06-18 | 0.97 | 06/18/2029 | 0.0000 |
| ID_NUMBER | DEMO482155 | 0.96 | DEMO-4821-55 | 0.0000 |
| NAME_DETAILS.FIRST_NAME | ELENA | 0.94 | ELENA | 0.0000 |
| NAME_DETAILS.LAST_NAME | MARTINEZ | 0.62 | MARTINEZ | 0.0000 |
| NAME_DETAILS.MIDDLE_NAME | MARTINEZ | 0.98 | — | 0.0000 |
| NAME_DETAILS.SUFFIX | — | 0.99 | — | 0.0000 |
| PERSONAL_DETAILS.EYE_COLOR | — | — | — | 0.0000 |
| PERSONAL_DETAILS.HAIR_COLOR | — | — | — | 0.0000 |
| PERSONAL_DETAILS.HEIGHT | — | — | — | 0.0000 |
| PERSONAL_DETAILS.SEX | F | 1.00 | F | 0.0000 |
| PERSONAL_DETAILS.WEIGHT | — | — | — | 0.0000 |
| RESTRICTIONS | NONE | 0.98 | NONE | 0.0000 |
| STATE_NAME | — | 0.13 | NEVADA | 0.0000 |


## synthetic-public-benefits-income-proof-pay-stub.jpg

**Durations**

- bda: 26.6s extraction
- llm: 10.305s extraction

| Field | BDA Value | Conf | LLM Value | LLM Conf |
|---|---|---|---|---|
| CityTaxes.ItemDescription | — | — | — | 0.0000 |
| CityTaxes.Period | — | — | — | 0.0000 |
| CityTaxes.YTD | — | — | — | 0.0000 |
| CompanyAddress.City | Hartford | 0.94 | Hartford | 0.0000 |
| CompanyAddress.Line1 | 1234 Community Way | 0.95 | 1234 Community Way | 0.0000 |
| CompanyAddress.Line2 | — | 0.95 | — | 0.0000 |
| CompanyAddress.State | ST | 0.92 | ST | 0.0000 |
| CompanyAddress.ZipCode | 06103 | 0.94 | 06103 | 0.0000 |
| CurrentGrossPay | 1350 | 0.95 | $1,350.00 | 0.0000 |
| CurrentNetPay | 1037.56 | 0.94 | $1,037.56 | 0.0000 |
| CurrentTotalDeductions | 312.44 | 0.45 | $312.44 | 0.0000 |
| EmployeeAddress.City | — | 0.93 | Hartford | 0.0000 |
| EmployeeAddress.Line1 | — | 0.94 | 1234 Community Way | 0.0000 |
| EmployeeAddress.Line2 | — | 0.95 | — | 0.0000 |
| EmployeeAddress.State | — | 0.92 | ST | 0.0000 |
| EmployeeAddress.ZipCode | — | 0.94 | 06103 | 0.0000 |
| EmployeeName.FirstName | Elena | 0.95 | Elena | 0.0000 |
| EmployeeName.LastName | Martinez | 0.90 | Martinez | 0.0000 |
| EmployeeName.MiddleName | — | 0.93 | — | 0.0000 |
| EmployeeName.SuffixName | — | 0.94 | — | 0.0000 |
| EmployeeNumber | EMP-78245 | 0.90 | EMP-78245 | 0.0000 |
| FederalFilingStatus | — | 0.94 | — | 0.0000 |
| FederalTaxes.ItemDescription | — | — | Federal Income Tax | 0.0000 |
| FederalTaxes.Period | — | — | $152.10 | 0.0000 |
| FederalTaxes.YTD | — | — | $1,064.70 | 0.0000 |
| HolidayHourlyRate | — | 0.95 | — | 0.0000 |
| PayDate | 2026-04-03 | 0.80 | 04/03/2026 | 0.0000 |
| PayPeriodEndDate | 2026-03-31 | 0.89 | 03/31/2026 | 0.0000 |
| PayPeriodStartDate | 2026-03-16 | 0.88 | 03/16/2026 | 0.0000 |
| PayrollNumber | — | 0.95 | — | 0.0000 |
| RegularHourlyRate | 16.88 | 0.95 | $16.88 | 0.0000 |
| StateFilingStatus | — | 0.94 | — | 0.0000 |
| StateTaxes.ItemDescription | — | — | State Income Tax | 0.0000 |
| StateTaxes.Period | — | — | $59.48 | 0.0000 |
| StateTaxes.YTD | — | — | $416.36 | 0.0000 |
| YTDCityTax | — | 0.95 | — | 0.0000 |
| YTDFederalTax | 1064.7 | 0.96 | $1,064.70 | 0.0000 |
| YTDGrossPay | 9450 | 0.96 | $9,450.00 | 0.0000 |
| YTDNetPay | 6562.92 | 0.95 | $6,562.92 | 0.0000 |
| YTDStateTax | 416.36 | 0.95 | $416.36 | 0.0000 |
| YTDTotalDeductions | 2887.08 | 0.58 | $2,887.08 | 0.0000 |
| are_field_names_sufficient | True | 0.07 | — | 0.0000 |
| currency | USD | 0.92 | USD | 0.0000 |
| is_gross_pay_valid | True | 0.92 | — | 0.0000 |
| is_ytd_gross_pay_highest | True | 0.92 | — | 0.0000 |


## synthetic-snap-income-proof-employment-wage-verification-letter-rendered.png

**Durations**

- bda: 28.22s extraction
- llm: 1.757s extraction

| Field | BDA Value | Conf | LLM Value | LLM Conf |
|---|---|---|---|---|
| employee_name | Luis Mendoza | 0.91 | Luis Mendoza | 1.0000 |
| employer_name | Harbor Home Care Service | 0.95 | Harbor Home Care Service | 1.0000 |
| employment_end_date | — | 0.94 | — | — |
| employment_start_date | August 12, 2024 | 0.83 | August 12, 2024 | 1.0000 |
| issuer_name | Dana Whitfield | 0.95 | Dana Whitfield | 0.0000 |
| issuer_title | Human Resources Manager | 0.93 | Human Resources Manager | 0.0000 |
| job_title | Home Health Aide | 0.89 | Home Health Aide | 1.0000 |
| salary_or_wage | $19.00 per hour | 0.27 | $19.00 per hour | 1.0000 |
