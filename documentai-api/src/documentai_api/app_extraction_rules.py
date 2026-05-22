"""Extraction rule configuration endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from documentai_api.annotations import AuthUser
from documentai_api.config.constants import ApiVisualizationTag
from documentai_api.logging import get_logger
from documentai_api.models.api_responses import (
    ExtractionRuleDeleteResponse,
    ExtractionRuleItem,
    ExtractionRulesListResponse,
)
from documentai_api.utils.auth import verify_api_key

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key)])


class ExtractionRuleRequest(BaseModel):
    """Request body for creating/updating an extraction rule."""

    document_type: str = Field(description="Document type this rule applies to")
    required_fields: list[str] = Field(description="Fields that must be present")
    optional_fields: list[str] = Field(
        default_factory=list, description="Fields that may be present"
    )


@router.get(
    "/v1/config/extraction-rules",
    name="getExtractionRules",
    response_model=ExtractionRulesListResponse,
    tags=[ApiVisualizationTag.CONFIG_RULES],
)
async def get_extraction_rules(
    auth: AuthUser,
    document_type: str | None = None,
) -> Any:
    """Get extraction rules for the authenticated tenant."""
    from documentai_api.utils.extraction_rules import get_rules

    rules = get_rules(auth.tenant_id, document_type)

    if not rules:
        if document_type:
            raise HTTPException(status_code=404, detail="No rules found")
        return ExtractionRulesListResponse(rules=[])
    return ExtractionRulesListResponse(rules=[ExtractionRuleItem(**r) for r in rules])


@router.put(
    "/v1/config/extraction-rules",
    name="putExtractionRule",
    response_model=ExtractionRuleItem,
    tags=[ApiVisualizationTag.CONFIG_RULES],
)
async def put_extraction_rule(
    auth: AuthUser,
    body: ExtractionRuleRequest,
) -> Any:
    """Create or update an extraction rule for the authenticated tenant."""
    from documentai_api.utils.extraction_rules import upsert_rule

    rule = upsert_rule(
        auth.tenant_id, body.document_type, body.required_fields, body.optional_fields
    )
    return ExtractionRuleItem(**rule)


@router.delete(
    "/v1/config/extraction-rules",
    name="deleteExtractionRule",
    response_model=ExtractionRuleDeleteResponse,
    tags=[ApiVisualizationTag.CONFIG_RULES],
)
async def delete_extraction_rule(
    auth: AuthUser,
    document_type: str,
) -> Any:
    """Delete an extraction rule for the authenticated tenant."""
    from documentai_api.utils.extraction_rules import delete_rule

    deleted = delete_rule(auth.tenant_id, document_type)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")
    return ExtractionRuleDeleteResponse(message="Rule deleted")
