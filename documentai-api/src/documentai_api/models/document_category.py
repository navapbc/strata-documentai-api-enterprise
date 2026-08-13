"""Request and response models for document category endpoints."""

from typing import Annotated

from pydantic import Field, StringConstraints

from documentai_api.models.base import BaseApiResponse

CategoryNameStr = Annotated[
    str, StringConstraints(pattern=r"^[a-z0-9_-]+$", min_length=1, max_length=64)
]


class CreateDocumentCategoryRequest(BaseApiResponse):
    category_name: CategoryNameStr
    display_name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    processing_percentage: float = Field(default=1.0, ge=0.0, le=1.0)


class UpdateDocumentCategoryRequest(BaseApiResponse):
    display_name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    is_active: bool | None = None
    processing_percentage: float | None = Field(default=None, ge=0.0, le=1.0)


class DocumentCategoryItem(BaseApiResponse):
    tenant_id: str
    category_name: str
    display_name: str
    description: str = ""
    is_active: bool = True
    is_auto_registered: bool = False
    processing_percentage: float = 1.0
    created_at: str | None = None
    updated_at: str | None = None


class ListDocumentCategoriesResponse(BaseApiResponse):
    categories: list[DocumentCategoryItem]
    count: int


class DeleteDocumentCategoryResponse(BaseApiResponse):
    deleted: bool
    category_name: str
