"""Response models for dictionary endpoints."""

from documentai_api.models.base import BaseApiResponse


class DictionaryFieldItem(BaseApiResponse):
    document_type: str
    name: str
    type: str
    description: str


class DictionaryFieldsResponse(BaseApiResponse):
    fields: list[DictionaryFieldItem]


class DictionarySearchResponse(BaseApiResponse):
    fields: list[DictionaryFieldItem]


class DictionarySchemaItem(BaseApiResponse):
    document_type: str
    description: str
    category: str
    field_count: int


class DictionarySchemaListResponse(BaseApiResponse):
    schemas: list[DictionarySchemaItem]


class DictionarySchemaFieldResponse(BaseApiResponse):
    name: str
    type: str
    description: str


class DictionarySchemaDetailResponse(BaseApiResponse):
    document_type: str
    fields: list[DictionarySchemaFieldResponse]
    category: str | None = None


class DictionaryResponseCodeItem(BaseApiResponse):
    code: str
    message: str


class DictionaryResponseCodesResponse(BaseApiResponse):
    response_codes: list[DictionaryResponseCodeItem]
