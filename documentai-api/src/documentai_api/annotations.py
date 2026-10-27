"""Shared type annotations for FastAPI endpoint parameters.

Centralizes repeated Annotated types so endpoint signatures stay DRY.
Import and use directly as parameter type hints.
"""

from typing import Annotated, Any, Literal

from fastapi import Depends, Form, Header, Query
from pydantic import Field, StringConstraints

from documentai_api.constants.processing import (
    OutputFormatType,
    UploadSource,
)
from documentai_api.utils.auth import (
    UserContext,
    get_user_context_from_api_key,
    get_user_context_with_fallback,
    is_presentation_mode,
    verify_jwt_with_role,
    verify_jwt_with_super_admin,
)

AuthMethod = Literal["api_key", "jwt"]


AdminClaims = Annotated[dict[str, Any], Depends(verify_jwt_with_role)]
SuperAdminClaims = Annotated[dict[str, Any], Depends(verify_jwt_with_super_admin)]
IsPresentationMode = Annotated[bool, Depends(is_presentation_mode)]

# Auth
# Router-level `dependencies=[Depends(get_user_context_from_api_key)]` enforces auth even if a handler
# forgets to inject `auth`. FastAPI caches the call within a request, so the per-handler
# `Depends(get_user_context_from_api_key)` via AuthUser is free (no double execution).
AuthUser = Annotated[UserContext, Depends(get_user_context_from_api_key)]
AuthUserWithFallback = Annotated[UserContext, Depends(get_user_context_with_fallback)]

# Headers
TraceId = Annotated[str | None, Header(alias="X-Trace-ID")]

# Common form fields
# Tenants submit free-form categories (auto-registered per tenant in the
# document_categories table). Validate for hygiene only - not against a fixed
# allowlist: strip + lowercase, then enforce a safe charset and length so the
# value is safe as a DDB sort key, cache-key segment, and preclassification
# prompt input.
DocumentCategoryField = Annotated[
    str | None,
    Form(description="Type of document being uploaded"),
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9 _-]+$",
    ),
]
UploadSourceField = Annotated[
    UploadSource | None, Form(description="Source device type of the upload (desktop or mobile)")
]
ExternalDocumentId = Annotated[
    str | None,
    Form(description="External document identifier"),
    StringConstraints(max_length=256, pattern=r"^[\w.\-/]+$"),
]
ExternalSystemId = Annotated[
    str | None,
    Form(description="External system identifier"),
    StringConstraints(max_length=128, pattern=r"^[\w.\-]+$"),
]
AiConsentFlag = Annotated[
    bool,
    Form(
        description=(
            "Explicit AI processing consent. "
            "True = consent granted, processing proceeds normally. "
            "False = consent denied, document is stored but not processed."
        )
    ),
]


# Query params
OutputFormat = Annotated[OutputFormatType, Query(alias="format")]
PageLimit = Annotated[int, Query(ge=1, le=200)]
IsoDateParam = Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}")]
MonthParam = Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}$")]

# Validated string types
ApiKeyNameStr = Annotated[
    str, StringConstraints(pattern=r"^[a-z0-9-]+$", min_length=1, max_length=64)
]
WriteLimit = Annotated[int, Field(gt=0, description="Maximum number of write requests allowed.")]

TenantIdField = Annotated[str, Form(description="Tenant identifier")]
