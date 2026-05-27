"""Admin API router - API key management via Cognito JWT auth."""

import hashlib

from fastapi import APIRouter, Depends, HTTPException, status

from documentai_api.annotations import AdminClaims
from documentai_api.config.constants import ApiVisualizationTag
from documentai_api.logging import get_logger
from documentai_api.models.api_key import (
    ApiKeyItem,
    CreateApiKeyRequest,
    CreateApiKeyResponse,
    DeleteApiKeyResponse,
    ListApiKeysResponse,
)
from documentai_api.schemas.api_key import ApiKeyRecord
from documentai_api.schemas.audit_event import AuditAction, AuditTargetType
from documentai_api.utils.audit import log_event
from documentai_api.utils.auth import (
    deactivate_api_key,
    find_api_key_by_prefix,
    generate_api_key,
)
from documentai_api.utils.jwt_auth import resolve_tenant, tenant_scope, verify_jwt

logger = get_logger(__name__)

# Router-level dependency only verifies the JWT. Per-handler `AdminClaims`
# additionally requires a role assignment, so pending users get a 403 there.
router = APIRouter(
    prefix="/v1/admin",
    tags=[ApiVisualizationTag.ADMIN_API_KEYS],
    dependencies=[Depends(verify_jwt)],
)


@router.post("/api-keys")
async def create_api_key(
    body: CreateApiKeyRequest,
    claims: AdminClaims,
) -> CreateApiKeyResponse:
    """Create a new API key for a client."""
    api_key_name = body.api_key_name
    environment = body.environment
    expires_at = body.expires_at
    email_address = body.email_address

    # JWT must be an ID token to carry email; fall back to sub for createdBy.
    created_by = claims.get("email") or claims.get("sub")
    # If the caller didn't supply an owner email, default to the admin's own.
    if email_address is None and claims.get("email"):
        email_address = claims["email"]

    # Resolve tenant - required for key creation
    effective_tenant = resolve_tenant(claims, body.tenant_id)
    if not effective_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id is required when creating keys as super-admin.",
        )

    # Validate tenant exists
    from documentai_api.utils.tenants import get_tenant

    if not get_tenant(effective_tenant):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant '{effective_tenant}' does not exist.",
        )

    # Check for duplicate key name within the same tenant
    from documentai_api.utils.auth import is_duplicate_key_name

    if is_duplicate_key_name(effective_tenant, api_key_name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An active key named '{api_key_name}' already exists for this tenant.",
        )

    try:
        api_key, existing_keys = generate_api_key(
            api_key_name=api_key_name,
            environment=environment,
            expires_at=expires_at,
            created_by=created_by,
            email_address=email_address,
            tenant_id=effective_tenant,
        )
    except Exception as e:
        logger.error(f"Failed to generate API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate API key",
        ) from e
    log_event(
        claims,
        action=AuditAction.KEY_CREATE,
        target_type=AuditTargetType.KEY,
        target_id=hashlib.sha256(api_key.encode()).hexdigest()[:8],
        tenant_id=effective_tenant,
        metadata={
            "api_key_name": api_key_name,
            "environment": environment,
            "expires_at": str(expires_at) if expires_at else None,
            "email_address": email_address,
        },
    )
    return CreateApiKeyResponse(
        api_key=api_key,
        api_key_name=api_key_name,
        environment=environment,
        expires_at=expires_at,
        existing_active_keys=len(existing_keys) if existing_keys else 0,
        created_by=created_by,
    )


@router.get("/api-keys")
async def list_api_keys(
    claims: AdminClaims,
    api_key_name: str | None = None,
    include_inactive: bool = False,
    tenant_id: str | None = None,
) -> ListApiKeysResponse:
    """List API keys.

    By default returns only active keys. Pass ``include_inactive=true`` to
    return both active and revoked keys.
    """
    from documentai_api.config.env import get_aws_config
    from documentai_api.services import ddb as ddb_service

    effective_tenant = resolve_tenant(claims, tenant_id)

    try:
        table_name = get_aws_config().api_keys_table_name
        if not table_name:
            raise ValueError("API_KEYS_TABLE_NAME not configured")
        all_records = ddb_service.scan(table_name)

        # Filter by effective tenant
        if effective_tenant is not None:
            all_records = [
                r for r in all_records if r.get(ApiKeyRecord.TENANT_ID) == effective_tenant
            ]
        if api_key_name:
            all_records = [
                r for r in all_records if r.get(ApiKeyRecord.API_KEY_NAME) == api_key_name
            ]
        records = (
            all_records
            if include_inactive
            else [r for r in all_records if r.get(ApiKeyRecord.IS_ACTIVE, False)]
        )
    except Exception as e:
        logger.error(f"Failed to list API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list API keys",
        ) from e

    # Redact key hashes for security
    items = [
        ApiKeyItem(
            api_key_name=record.get(ApiKeyRecord.API_KEY_NAME),
            tenant_id=record.get(ApiKeyRecord.TENANT_ID),
            environment=record.get(ApiKeyRecord.ENVIRONMENT),
            is_active=record.get(ApiKeyRecord.IS_ACTIVE),
            created_at=record.get(ApiKeyRecord.CREATED_AT),
            expires_at=record.get(ApiKeyRecord.EXPIRES_AT),
            last_used=record.get(ApiKeyRecord.LAST_USED),
            created_by=record.get(ApiKeyRecord.CREATED_BY),
            email_address=record.get(ApiKeyRecord.EMAIL_ADDRESS),
            key_prefix=record.get(ApiKeyRecord.KEY_HASH, "")[:8],
        )
        for record in records
    ]
    return ListApiKeysResponse(keys=items, count=len(items))


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    claims: AdminClaims,
) -> DeleteApiKeyResponse:
    """Deactivate an API key by full hash or hash prefix.

    Tenant-admins can only delete keys belonging to their tenant; super-admins
    can delete any key.
    """
    caller_tenant = tenant_scope(claims)

    if len(key_id) == 64:
        full_hash = key_id
        # For a full-hash delete, still enforce tenant scoping by reading the
        # record and rejecting if the caller isn't allowed to touch it.
        if caller_tenant is not None:
            from documentai_api.config.env import get_aws_config
            from documentai_api.services import ddb as ddb_service

            table_name = get_aws_config().api_keys_table_name
            if not table_name:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="API_KEYS_TABLE_NAME not configured",
                )
            record = ddb_service.get_item(table_name, {ApiKeyRecord.KEY_HASH: full_hash})
            if not record or record.get(ApiKeyRecord.TENANT_ID) != caller_tenant:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    else:
        try:
            full_hash = find_api_key_by_prefix(key_id, tenant_id=caller_tenant)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
        if not full_hash:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")

    if not deactivate_api_key(full_hash):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")

    log_event(
        claims,
        action=AuditAction.KEY_REVOKE,
        target_type=AuditTargetType.KEY,
        target_id=full_hash[:8],
        tenant_id=caller_tenant,
    )
    return DeleteApiKeyResponse(deactivated=True, key_id=full_hash[:8])
