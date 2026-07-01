"""Map Textract AnalyzeID field types directly to BDA blueprint field names for US driver's licenses.

See: https://docs.aws.amazon.com/textract/latest/dg/identitydocumentfields.html
"""

# Fields normalized by AnalyzeID into IdentityDocumentFields
FIELD_MAP = {
    "FIRST_NAME": "NAME_DETAILS.FIRST_NAME",
    "MIDDLE_NAME": "NAME_DETAILS.MIDDLE_NAME",
    "LAST_NAME": "NAME_DETAILS.LAST_NAME",
    "SUFFIX": "NAME_DETAILS.SUFFIX",
    "ADDRESS": "ADDRESS_DETAILS.STREET_ADDRESS",
    "CITY_IN_ADDRESS": "ADDRESS_DETAILS.CITY",
    "ZIP_CODE_IN_ADDRESS": "ADDRESS_DETAILS.ZIP_CODE",
    "STATE_IN_ADDRESS": "ADDRESS_DETAILS.STATE",
    "COUNTY": "COUNTY",
    "DOCUMENT_NUMBER": "ID_NUMBER",
    "EXPIRATION_DATE": "EXPIRATION_DATE",
    "DATE_OF_BIRTH": "DATE_OF_BIRTH",
    "STATE_NAME": "STATE_NAME",
    "DATE_OF_ISSUE": "DATE_OF_ISSUE",
    "CLASS": "CLASS",
    "RESTRICTIONS": "RESTRICTIONS",
    "ENDORSEMENTS": "ENDORSEMENTS",
}

# Fields present in AnalyzeID raw OCR (Blocks) but not normalized into
# IdentityDocumentFields. Extracted via Nova Micro as a supplemental pass.
NON_NORMALIZED_ANALYZE_ID_FIELDS = {
    "PERSONAL_DETAILS.SEX": "Sex/Gender (e.g. M, F)",
    "PERSONAL_DETAILS.HEIGHT": "Height (e.g. 5-06, 5'06\")",
    "PERSONAL_DETAILS.EYE_COLOR": "Eye color (e.g. BRN, BLK, BLU, GRN, HAZ)",
    "PERSONAL_DETAILS.HAIR_COLOR": "Hair color (e.g. BRN, BLK, BLN, RED, GRY)",
    "PERSONAL_DETAILS.WEIGHT": "Weight in pounds (e.g. 150)",
}

# Prompt for Nova Micro to extract NON_NORMALIZED_ANALYZE_ID_FIELDS from Blocks.
# DL-specific: references physical descriptor label conventions on US licenses.
NOVA_SUPPLEMENTAL_PROMPT = """Given the following OCR word blocks from a US driver's license, extract these physical descriptor fields:

{field_descriptions}

Word blocks (text and bounding box):
{blocks_json}

Respond in JSON only:
{{
  "fields": [
    {{"field_name": "<field_name>", "value": "<extracted_value>", "block_index": <index of block in the array>}}
  ]
}}

Rules:
- Physical descriptors (SEX, HGT, EYES, HAIR, WT) are typically grouped together on the lower half of the license, near their label abbreviations.
- Only extract values that appear immediately adjacent to or below their corresponding label (e.g. "F" next to "SEX", "BLK" next to "EYES").
- Do NOT use address numbers, document numbers, or date values as physical descriptor values.
- "block_index" - return the "index" value from the word block where the value was found.
- If a field cannot be confidently identified from nearby labels, omit it.
- Do not invent values.
"""
