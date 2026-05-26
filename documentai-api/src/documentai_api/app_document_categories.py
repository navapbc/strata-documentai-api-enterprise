"""Admin document categories router — CRUD for tenant document categories."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from documentai_api.annotations import AdminClaims, verify_jwt_with_role
from documentai_api.config.constants import ApiVisualizationTag
from documentai_api.logging import get_logger
from documentai_api.models.document_category import (
    CreateDocumentCategoryRequest,
    DocumentCategoryItem,
    ListDocumentCategoriesResponse,
    UpdateDocumentCategoryRequest,
)
from documentai_api.schemas.document_category import DocumentCategoryRecord
from documentai_api.utils import document_categories as categories_util
from documentai_api.utils.jwt_auth import resolve_tenant, tenant_scope

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1/admin/document-categories",
    tags=[ApiVisualizationTag.ADMIN_CATEGORIES],
    dependencies=[Depends(verify_jwt_with_role)],
)


def _get_effective_tenant(claims: dict[str, Any], tenant_id: str | None = None) -> str:
    """Resolve tenant — required for all category operations."""
    scope = tenant_scope(claims)
    if scope is not None:
        if tenant_id and tenant_id != scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant.",
            )
        return scope
    effective = resolve_tenant(claims, tenant_id)
    if not effective:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required for super-admin operations.",
        )
    return effective


def _to_item(record: dict[str, Any]) -> DocumentCategoryItem:
    return DocumentCategoryItem(
        tenant_id=record.get(DocumentCategoryRecord.TENANT_ID, ""),
        category_name=record.get(DocumentCategoryRecord.CATEGORY_NAME, ""),
        display_name=record.get(DocumentCategoryRecord.DISPLAY_NAME, ""),
        description=record.get(DocumentCategoryRecord.DESCRIPTION, ""),
        is_active=record.get(DocumentCategoryRecord.IS_ACTIVE, True),
        created_at=record.get(DocumentCategoryRecord.CREATED_AT),
        updated_at=record.get(DocumentCategoryRecord.UPDATED_AT),
    )


@router.get("")
async def list_document_categories(
    claims: AdminClaims,
    tenant_id: str | None = None,
    active_only: bool = True,
) -> ListDocumentCategoriesResponse:
    """List document categories.

    Super-admins can omit tenant_id to list all categories across tenants.
    Tenant-admins are locked to their own tenant.
    """
    scope = tenant_scope(claims)
    if scope is not None:
        if tenant_id and tenant_id != scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant.",
            )
        tenant_id = scope

    if tenant_id:
        records = categories_util.list_categories(tenant_id, active_only=active_only)
    else:
        # Super-admin with no tenant filter — list all
        records = categories_util.list_all_categories(active_only=active_only)

    items = [_to_item(r) for r in records]
    return ListDocumentCategoriesResponse(categories=items, count=len(items))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_document_category(
    body: CreateDocumentCategoryRequest,
    claims: AdminClaims,
    tenant_id: str | None = None,
) -> DocumentCategoryItem:
    """Create a new document category for a tenant."""
    effective_tenant = _get_effective_tenant(claims, tenant_id)
    try:
        record = categories_util.create_category(
            tenant_id=effective_tenant,
            category_name=body.category_name,
            display_name=body.display_name,
            description=body.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    return _to_item(record)


@router.get("/{category_name}")
async def get_document_category(
    category_name: str,
    claims: AdminClaims,
    tenant_id: str | None = None,
) -> DocumentCategoryItem:
    """Get a single document category."""
    effective_tenant = _get_effective_tenant(claims, tenant_id)
    record = categories_util.get_category(effective_tenant, category_name)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return _to_item(record)


@router.patch("/{category_name}")
async def update_document_category(
    category_name: str,
    body: UpdateDocumentCategoryRequest,
    claims: AdminClaims,
    tenant_id: str | None = None,
) -> DocumentCategoryItem:
    """Update a document category."""
    effective_tenant = _get_effective_tenant(claims, tenant_id)
    try:
        updated = categories_util.update_category(
            effective_tenant,
            category_name,
            display_name=body.display_name,
            description=body.description,
            is_active=body.is_active,
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg) from e
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from e
    return _to_item(updated)


@router.delete("/{category_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_category(
    category_name: str,
    claims: AdminClaims,
    tenant_id: str | None = None,
) -> None:
    """Deactivate a document category (soft delete)."""
    effective_tenant = _get_effective_tenant(claims, tenant_id)
    if not categories_util.delete_category(effective_tenant, category_name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
