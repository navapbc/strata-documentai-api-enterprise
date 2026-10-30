# synthetic-investment-and-royalty-income-render.pdf

_Last run:: 2026-10-29 21:22 UTC_

## Durations

- bda: 25.1s extraction
- ocr-mapping: 2.589s extraction

## Cost

_By Service_

- us.amazon.nova-pro-v1:0: $0.01228800 (13172 in / 547 out)
- bda: $0.04000000 (1 page(s))
- analyze_document_layout: $0.00400000 (1 page(s))
- **total: $0.05628800**

_By Extraction Method_

- shared (preclassification): $0.00876640
- ocr-mapping extraction: $0.00752160
- primary (bda): $0.04000000
- **total: $0.05628800**

## Accuracy

_By Extracted Data_

- BDA: 6/6 (100%) equivalent match, 6/6 (100%) close, 0 misses
- OCR Mapping: 6/6 (100%) equivalent match, 6/6 (100%) close, 0 misses

_By Bounding Box_

- BDA: 2/6 exact, 3 miss
- OCR Mapping: 0/6 exact, 5 miss

## Field Comparison

| Field | Expected | BDA Value | OCR / LLM Value | BDA Conf | OCR / LLM Conf | Expected Bounding Box | BDA Bounding Box | OCR / LLM Bounding Box |
|---|---|---|---|---|---|---|---|---|
| account_balance | $49,000.00 | ✅ $49,000.00 | ✅ $49,000.00 | 0.37 | 1.0000 | 0.779,0.684,0.087,0.013 | ✅ 0.778,0.683,0.088,0.014 | ❌ 0.130,0.684,0.267,0.014 |
| account_holder_name | Jordan Rivera | ✅ Jordan Rivera | ✅ Jordan Rivera | 0.91 | N/A | 0.117,0.254,0.679,0.016 | 🟡 0.117,0.254,0.112,0.012 | ❌ 0.116,0.228,0.135,0.012 |
| account_number | xxxx-xxxx-1392 | ✅ xxxx-xxxx-1392 | ✅ xxxx-xxxx-1392 | 0.84 | 0.9100 | 0.117,0.254,0.679,0.016 | ❌ 0.678,0.260,0.118,0.011 | ❌ 0.526,0.259,0.271,0.011 |
| account_type | Traditional IRA | ✅ Traditional IRA | ✅ Traditional IRA | 0.88 | 1.0000 | 0.117,0.229,0.673,0.014 | ❌ 0.678,0.229,0.112,0.011 | ❌ 0.525,0.229,0.265,0.011 |
| contribution_dates | - | - | ❌ 2025-01-01, 2025-12-31 | 0.93 | 1.0000 | - | - | 0.525,0.290,0.260,0.011 |
| distribution_dates | - | - | ❌ 2025-01-01, 2025-12-31 | 0.94 | 1.0000 | - | - | 0.525,0.290,0.260,0.011 |
| financial_institution | Seaport Financial Group | ✅ Seaport Financial Group | ✅ Seaport Financial Group | 0.87 | 0.9800 | 0.114,0.167,0.367,0.011 | ❌ 0.224,0.054,0.191,0.054 | 🟡 0.114,0.166,0.173,0.013 |
| tax_year | 2025 | ✅ 2025 | ✅ 2025 | 0.95 | 1.0000 | 0.748,0.290,0.037,0.010 | ✅ 0.748,0.290,0.038,0.011 | ❌ 0.525,0.290,0.260,0.011 |