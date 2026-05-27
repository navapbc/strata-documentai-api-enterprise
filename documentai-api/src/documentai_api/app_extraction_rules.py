"""Extraction rule configuration endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from documentai_api.annotations import AuthUserWithFallback
from documentai_api.config.constants import ApiVisualizationTag
from documentai_api.logging import get_logger
from documentai_api.models.extraction_rule import (
    ExtractionRuleDeleteResponse,
    ExtractionRuleItem,
    ExtractionRulesListResponse,
)
from documentai_api.schemas.audit_event import AuditAction, AuditTargetType
from documentai_api.utils.audit import log_event
from documentai_api.utils.auth import get_user_context_with_fallback

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(get_user_context_with_fallback)])


class ExtractionRuleRequest(BaseModel):
    """Request body for creating/updating an extraction rule."""

    document_type: str = Field(description="Document type this rule applies to")
    required_fields: list[str] = Field(description="Fields that must be present")
    optional_fields: list[str] = Field(
        default_factory=list, description="Fields that may be present"
    )
    tenant_id: str | None = Field(
        default=None,
        description="Target tenant. Required for super-admins; ignored for tenant-admins.",
    )
    blueprint_arn: str | None = Field(
        default=None,
        description="BDA blueprint ARN for stable reference across renames.",
    )


def _resolve_tenant(auth_tenant_id: str, body_tenant_id: str | None) -> str:
    """Determine the effective tenant for the operation.

    Tenant-admins (real tenant_id): always use their own, ignore body.
    Super-admins (__admin__): must provide tenant_id in body.
    API key users (real tenant_id): use their own.
    """
    if auth_tenant_id != "__admin__":
        return auth_tenant_id
    if not body_tenant_id:
        raise HTTPException(
            status_code=400,
            detail="tenant_id is required for super-admin operations.",
        )
    return body_tenant_id


@router.get(
    "/v1/config/extraction-rules",
    response_model=ExtractionRulesListResponse,
    tags=[ApiVisualizationTag.CONFIG_RULES],
)
async def get_extraction_rules(
    auth: AuthUserWithFallback,
    document_type: str | None = None,
    tenant_id: str | None = None,
) -> Any:
    """Get extraction rules for a tenant."""
    from documentai_api.utils.extraction_rules import get_rules

    effective_tenant = _resolve_tenant(auth.tenant_id, tenant_id)
    rules = get_rules(effective_tenant, document_type)

    if not rules:
        if document_type:
            raise HTTPException(status_code=404, detail="No rules found")
        return ExtractionRulesListResponse(rules=[])
    return ExtractionRulesListResponse(rules=[ExtractionRuleItem(**r) for r in rules])


@router.put(
    "/v1/config/extraction-rules",
    response_model=ExtractionRuleItem,
    tags=[ApiVisualizationTag.CONFIG_RULES],
)
async def put_extraction_rule(
    auth: AuthUserWithFallback,
    body: ExtractionRuleRequest,
) -> Any:
    """Create or update an extraction rule."""
    from documentai_api.utils.extraction_rules import upsert_rule

    effective_tenant = _resolve_tenant(auth.tenant_id, body.tenant_id)
    rule = upsert_rule(
        effective_tenant,
        body.document_type,
        body.required_fields,
        body.optional_fields,
        blueprint_arn=body.blueprint_arn,
    )
    log_event(
        claims={"sub": auth.api_key_name, "email": auth.api_key_name},
        action=AuditAction.EXTRACTION_RULE_UPDATE,
        target_type=AuditTargetType.EXTRACTION_RULE,
        target_id=body.document_type,
        tenant_id=effective_tenant,
    )
    return ExtractionRuleItem(**rule)


@router.delete(
    "/v1/config/extraction-rules",
    response_model=ExtractionRuleDeleteResponse,
    tags=[ApiVisualizationTag.CONFIG_RULES],
)
async def delete_extraction_rule(
    auth: AuthUserWithFallback,
    document_type: str,
    tenant_id: str | None = None,
) -> Any:
    """Delete an extraction rule."""
    from documentai_api.utils.extraction_rules import delete_rule

    effective_tenant = _resolve_tenant(auth.tenant_id, tenant_id)
    deleted = delete_rule(effective_tenant, document_type)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")
    log_event(
        claims={"sub": auth.api_key_name, "email": auth.api_key_name},
        action=AuditAction.EXTRACTION_RULE_DELETE,
        target_type=AuditTargetType.EXTRACTION_RULE,
        target_id=document_type,
        tenant_id=effective_tenant,
    )
    return ExtractionRuleDeleteResponse(message="Rule deleted")
