_Run: 2026-09-25 01:00 UTC_


## synthetic-public-benefits-identity-proof-state-photo-id.jpg

**Durations**

- llm: 9.413s extraction
- textract: 2.14s extraction

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
