"""Admin audit log router — read-only access to audit events."""

from typing import Any

from boto3.dynamodb.conditions import Attr, ConditionBase, Key
from fastapi import APIRouter, Depends, HTTPException, status

from documentai_api.annotations import AdminClaims, IsoDateParam, PageLimit, verify_jwt_with_role
from documentai_api.logging import get_logger
from documentai_api.models.audit import AuditActionsResponse, AuditEventItem, AuditLogResponse
from documentai_api.schemas.audit_event import (
    GLOBAL_TENANT,
    AuditAction,
    AuditEventRecord,
    AuditEventsTable,
)
from documentai_api.utils.jwt_auth import tenant_scope
from documentai_api.utils.pagination import decode_cursor, encode_cursor

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1/admin/audit-log",
    tags=["admin-audit-log"],
    dependencies=[Depends(verify_jwt_with_role)],
)


_table = AuditEventsTable()


def _record_to_item(record: dict[str, Any]) -> AuditEventItem:
    sort_key = record.get(AuditEventRecord.TIMESTAMP_EVENT_ID, "")
    timestamp = sort_key.split("#")[0] if "#" in sort_key else sort_key
    return AuditEventItem(
        event_id=record.get(AuditEventRecord.EVENT_ID, ""),
        tenant_id=record.get(AuditEventRecord.TENANT_ID, ""),
        actor_sub=record.get(AuditEventRecord.ACTOR_SUB, ""),
        actor_email=record.get(AuditEventRecord.ACTOR_EMAIL, ""),
        action=record.get(AuditEventRecord.ACTION, ""),
        target_type=record.get(AuditEventRecord.TARGET_TYPE, ""),
        target_id=record.get(AuditEventRecord.TARGET_ID, ""),
        metadata=record.get(AuditEventRecord.METADATA, {}),
        timestamp=timestamp,
    )


@router.get("/actions")
async def get_audit_actions() -> AuditActionsResponse:
    """Return all known audit action strings."""
    actions = [
        v for k, v in vars(AuditAction).items() if not k.startswith("_") and isinstance(v, str)
    ]
    return AuditActionsResponse(actions=sorted(actions))


@router.get("")
async def get_audit_log(
    claims: AdminClaims,
    tenant_id: str | None = None,
    action: str | None = None,
    start_date: IsoDateParam = None,
    end_date: IsoDateParam = None,
    limit: PageLimit = 50,
    cursor: str | None = None,
) -> AuditLogResponse:
    """Query audit events.

    Super-admins can query any tenant or by action (via GSI).
    Tenant-admins can only query their own tenant's events.
    """
    scope = tenant_scope(claims)

    # Tenant-admins are locked to their own partition
    if scope is not None:
        if tenant_id and tenant_id != scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant's audit log.",
            )
        tenant_id = scope

    try:
        exclusive_start_key = decode_cursor(cursor) if cursor else None

        if action and not tenant_id:
            # Super-admin querying by action across all tenants (GSI)
            records, last_key = _query_by_action(
                action, start_date, end_date, limit, exclusive_start_key
            )
        else:
            # Query by tenant partition
            partition = tenant_id or GLOBAL_TENANT
            records, last_key = _query_by_tenant(
                partition, action, start_date, end_date, limit, exclusive_start_key
            )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to query audit log: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query audit log",
        ) from e

    items = [_record_to_item(r) for r in records]
    next_cursor = encode_cursor(last_key) if last_key else None
    return AuditLogResponse(events=items, count=len(items), next_cursor=next_cursor)


def _build_sk_condition(start_date: str | None, end_date: str | None) -> ConditionBase | None:
    """Build sort key condition for date range filtering."""
    sk = Key(AuditEventRecord.TIMESTAMP_EVENT_ID)
    if start_date and end_date:
        return sk.between(start_date, end_date + "~")
    elif start_date:
        return sk.gte(start_date)
    elif end_date:
        return sk.lte(end_date + "~")
    return None


def _query_by_tenant(
    tenant_id: str,
    action: str | None,
    start_date: str | None,
    end_date: str | None,
    limit: int,
    exclusive_start_key: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    key_condition: ConditionBase = Key(AuditEventRecord.TENANT_ID).eq(tenant_id)
    sk_condition = _build_sk_condition(start_date, end_date)
    if sk_condition:
        key_condition = key_condition & sk_condition

    filter_expr = Attr(AuditEventRecord.ACTION).eq(action) if action else None

    return _table.query(
        key_condition=key_condition,
        filter_expression=filter_expr,
        limit=limit,
        scan_forward=False,
        start_key=exclusive_start_key,
    )


def _query_by_action(
    action: str,
    start_date: str | None,
    end_date: str | None,
    limit: int,
    exclusive_start_key: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    key_condition: ConditionBase = Key(AuditEventRecord.ACTION).eq(action)
    sk_condition = _build_sk_condition(start_date, end_date)
    if sk_condition:
        key_condition = key_condition & sk_condition

    return _table.query(
        key_condition=key_condition,
        index_name="action-timestamp-index",
        limit=limit,
        scan_forward=False,
        start_key=exclusive_start_key,
    )
