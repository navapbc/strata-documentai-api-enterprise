"""Map Textract AnalyzeID field types directly to BDA blueprint field names for US driver's licenses.

Note: AnalyzeID does not return physical descriptor fields (SEX, HEIGHT, WEIGHT,
EYE_COLOR, HAIR_COLOR) that BDA extracts. These are intentionally omitted from
the map.

See: https://docs.aws.amazon.com/textract/latest/dg/identitydocumentfields.html
"""

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
