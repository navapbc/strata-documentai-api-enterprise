from enum import StrEnum


class DictionaryBlueprintSchema(StrEnum):
    FIELDS = "fields"


class DictionaryBlueprintField(StrEnum):
    NAME = "name"
    TYPE = "type"
    DESCRIPTION = "description"
    DOCUMENT_TYPE = "documentType"
