"""Request model for auth event reporting."""

from pydantic import BaseModel


class AuthEventRequest(BaseModel):
    action: str
    email: str | None = None
    metadata: dict[str, str] | None = None
