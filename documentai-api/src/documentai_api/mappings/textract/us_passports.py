"""Map Textract AnalyzeID field types directly to BDA blueprint field names for US passports.

See: https://docs.aws.amazon.com/textract/latest/dg/identitydocumentfields.html
"""

FIELD_MAP = {
    "FIRST_NAME": "name.given_name",
    "LAST_NAME": "name.last_name",
    "DOCUMENT_NUMBER": "document_number",
    "EXPIRATION_DATE": "expiration_date",
    "DATE_OF_BIRTH": "date_of_birth",
    "DATE_OF_ISSUE": "date_of_issue",
    "PLACE_OF_BIRTH": "place_of_birth",
    "MRZ_CODE": "mrz_code",
}

# Fields not normalized by AnalyzeID for passports. Extracted via Nova Micro.
NON_NORMALIZED_ANALYZE_ID_FIELDS = {
    "sex": "Sex/Gender (e.g. M, F)",
    "passport_type": "Passport type code (e.g. P)",
    "authority": "Issuing authority/country (e.g. UNITED STATES)",
}

NOVA_SUPPLEMENTAL_PROMPT = """Given the following OCR word blocks from a US passport, extract these fields:

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
- "block_index" - return the "index" value from the word block where the value was found.
- Sex is a single letter (M or F) that appears as a standalone block, not part of a date or MRZ line.
- Passport type is a single letter (typically "P") that appears as a standalone block near the document number.
- Authority is the issuing country. If the same text appears in multiple blocks, return the block_index of the one with the higher "left" bounding box value.
- If a field cannot be confidently identified, omit it.
- Do not invent values.
"""
