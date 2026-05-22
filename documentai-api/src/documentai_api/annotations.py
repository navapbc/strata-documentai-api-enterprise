"""Shared type annotations for FastAPI endpoint parameters.

Centralizes repeated Annotated types so endpoint signatures stay DRY.
Import and use directly as parameter type hints.
"""

from typing import Annotated

from fastapi import Depends, Form, Header, Query
from pydantic import StringConstraints

from documentai_api.config.constants import (
    DictionaryFormatType,
    DocumentCategory,
)
from documentai_api.utils.auth import UserContext, get_user_context

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
