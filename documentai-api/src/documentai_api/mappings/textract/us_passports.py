"""Map Textract AnalyzeID field types directly to BDA blueprint field names for US passports.

Note: AnalyzeID does not return physical descriptor fields (SEX, HEIGHT, WEIGHT,
EYE_COLOR, HAIR_COLOR) that BDA extracts. These are intentionally omitted from
the map.

See: https://docs.aws.amazon.com/textract/latest/dg/identitydocumentfields.html
"""

FIELD_MAP = {
    "FIRST_NAME": "name.given_name",
    "LAST_NAME": "name.last_name",
    "MIDDLE_NAME": "name.middle_name",
    "DOCUMENT_NUMBER": "document_number",
    "EXPIRATION_DATE": "expiration_date",
    "DATE_OF_BIRTH": "date_of_birth",
    "DATE_OF_ISSUE": "date_of_issue",
    "PLACE_OF_BIRTH": "place_of_birth",
    "MRZ_CODE": "mrz_code",
}
