export const DEMO_RULES = {
  "W2": {
    requiredFields: ["employer_name", "employee_name", "wages_tips_compensation", "tax_year"],
    optionalFields: ["employer_ein", "federal_income_tax_withheld"],
  },
  "Payslip": {
    requiredFields: ["employee_name", "gross_pay", "net_pay", "pay_date"],
    optionalFields: ["pay_period_start", "pay_period_end"],
  },
};
