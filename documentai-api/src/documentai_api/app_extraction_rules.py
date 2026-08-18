"""Extraction rule configuration endpoints."""

from typing import Any, Self

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator

from documentai_api.annotations import AuthUserWithFallback
from documentai_api.config.constants import ApiVisualizationTag
from documentai_api.logging import get_logger
from documentai_api.models.extraction_rule import (
    ExtractionRuleDeleteResponse,
    ExtractionRuleItem,
    ExtractionRulesListResponse,
)
from documentai_api.schemas.audit_event import AuditAction, AuditTargetType
from documentai_api.utils.audit_log import log_event
from documentai_api.utils.auth import get_user_context_with_fallback
from documentai_api.utils.field_labels import get_valid_fields

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

    @field_validator("document_type", mode="before")
    @classmethod
    def validate_document_type(cls, v: object) -> str:
        """Validate document type is a string."""
        if not isinstance(v, str):
            raise ValueError("document_type must be a string")

        return v

    @field_validator("required_fields", "optional_fields", mode="before")
    @classmethod
    def deduplicate_fields(cls, v: object) -> list[str]:
        """Remove duplicate field names preserving order."""
        if not isinstance(v, list):
            raise ValueError("must be a list of strings")

        seen: set[str] = set()
        result = []
        for f in v:
            key = f.lower() if isinstance(f, str) else f
            if key not in seen:
                seen.add(key)
                result.append(f)
        return result

    @model_validator(mode="after")
    def validate_fields(self) -> Self:
        """Validate and normalize field names to match exact names from label files."""
        valid_fields = get_valid_fields(self.document_type)

        if valid_fields is None:
            raise ValueError(
                f"Unknown document type '{self.document_type}'. Run pull-blueprint-fields first."
            )

        invalid = [
            f for f in self.required_fields + self.optional_fields if f.lower() not in valid_fields
        ]

        if invalid:
            raise ValueError(f"Unknown fields for '{self.document_type}': {invalid}")

        self.required_fields = [valid_fields[f.lower()] for f in self.required_fields]
        self.optional_fields = [valid_fields[f.lower()] for f in self.optional_fields]

        overlap = set(self.required_fields) & set(self.optional_fields)

        if overlap:
            raise ValueError(f"Fields cannot be both required and optional: {sorted(overlap)}")

        return self


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
