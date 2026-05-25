"""Request and response models for admin API endpoints."""

from pydantic import AwareDatetime

from documentai_api.annotations import ApiKeyNameStr
from documentai_api.models.base import BaseApiResponse


class CreateApiKeyRequest(BaseApiResponse):
    api_key_name: ApiKeyNameStr
    environment: str = "dev"
    email_address: str | None = None
    expires_at: AwareDatetime | None = None
    tenant_id: str | None = None


class CreateApiKeyResponse(BaseApiResponse):
    api_key: str
    api_key_name: str
    environment: str
    expires_at: AwareDatetime | None = None
    existing_active_keys: int = 0
    created_by: str | None = None


class ApiKeyItem(BaseApiResponse):
    api_key_name: str | None = None
    tenant_id: str | None = None
    environment: str | None = None
    is_active: bool | None = None
    created_at: str | None = None
    expires_at: str | None = None
    last_used: str | None = None
    created_by: str | None = None
    email_address: str | None = None
    key_prefix: str | None = None


class ListApiKeysResponse(BaseApiResponse):
    keys: list[ApiKeyItem]
    count: int


class DeleteApiKeyResponse(BaseApiResponse):
    deactivated: bool
    key_id: str
