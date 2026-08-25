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


class DictionarySchemaListResponse(BaseApiResponse):
    schemas: list[str]


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


class DictionaryDocumentCategoriesResponse(BaseApiResponse):
    document_categories: list[str]
