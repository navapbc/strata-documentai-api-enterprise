"""Shared type annotations for FastAPI endpoint parameters.

Centralizes repeated Annotated types so endpoint signatures stay DRY.
Import and use directly as parameter type hints.
"""

from typing import Annotated, Any

from fastapi import Depends, Form, Header, Query
from pydantic import StringConstraints

from documentai_api.config.constants import (
    DictionaryFormatType,
    DocumentCategory,
)
from documentai_api.utils.auth import UserContext, get_user_context
from documentai_api.utils.jwt_auth import require_role, require_super_admin, verify_jwt


async def verify_jwt_with_role(
    claims: Annotated[dict[str, Any], Depends(verify_jwt)],
) -> dict[str, Any]:
    """Verify the JWT and require that the user has been assigned a role.

    Pending users (authenticated but no Cognito group) get a 403 here so admin
    handlers never see them.
    """
    require_role(claims)
    return claims


async def verify_jwt_with_super_admin(
    claims: Annotated[dict[str, Any], Depends(verify_jwt)],
) -> dict[str, Any]:
    """Verify the JWT and require that the user is in the super-admin group."""
    require_super_admin(claims)
    return claims


AdminClaims = Annotated[dict[str, Any], Depends(verify_jwt_with_role)]
SuperAdminClaims = Annotated[dict[str, Any], Depends(verify_jwt_with_super_admin)]

# Auth
# Router-level `dependencies=[Depends(get_user_context)]` enforces auth even if a handler
# forgets to inject `auth`. FastAPI caches the call within a request, so the per-handler
# `Depends(get_user_context)` via AuthUser is free (no double execution).
AuthUser = Annotated[UserContext, Depends(get_user_context)]

# Headers
TraceId = Annotated[str | None, Header(alias="X-Trace-ID")]

# Common form fields
CategoryField = Annotated[
    DocumentCategory | None, Form(description="Type of document being uploaded")
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
OutputFormat = Annotated[DictionaryFormatType, Query(alias="format")]
