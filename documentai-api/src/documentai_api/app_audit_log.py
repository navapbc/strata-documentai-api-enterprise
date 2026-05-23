"""Admin audit log router — read-only access to audit events."""

import base64
import json
from typing import Any

from boto3.dynamodb.conditions import Attr, ConditionBase, Key
from fastapi import APIRouter, Depends, HTTPException, status

from documentai_api.annotations import AdminClaims, IsoDateParam, PageLimit, verify_jwt_with_role
from documentai_api.logging import get_logger
from documentai_api.models.audit import AuditEventItem, AuditLogResponse
from documentai_api.schemas.audit_event import GLOBAL_TENANT, AuditEventRecord
from documentai_api.utils.aws_client_factory import AWSClientFactory
from documentai_api.utils.jwt_auth import tenant_scope

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1/admin/audit-log",
    tags=["admin-audit-log"],
    dependencies=[Depends(verify_jwt_with_role)],
)


def _get_table_name() -> str:
    from documentai_api.config.env import get_aws_config

    table_name = get_aws_config().audit_events_table_name
    if not table_name:
        raise ValueError("AUDIT_EVENTS_TABLE_NAME not configured")
    return table_name


def _encode_cursor(last_key: dict[str, Any]) -> str:
    return base64.urlsafe_b64encode(json.dumps(last_key).encode()).decode()


def _decode_cursor(cursor: str) -> dict[str, Any]:
    try:
        result: dict[str, Any] = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return result
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor"
        ) from None


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
        table = AWSClientFactory.get_ddb_table(_get_table_name())
        exclusive_start_key = _decode_cursor(cursor) if cursor else None

        if action and not tenant_id:
            # Super-admin querying by action across all tenants (GSI)
            records, last_key = _query_by_action(
                table, action, start_date, end_date, limit, exclusive_start_key
            )
        else:
            # Query by tenant partition
            partition = tenant_id or GLOBAL_TENANT
            records, last_key = _query_by_tenant(
                table, partition, action, start_date, end_date, limit, exclusive_start_key
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
    next_cursor = _encode_cursor(last_key) if last_key else None
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
    table: Any,
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

    kwargs: dict[str, Any] = {
        "KeyConditionExpression": key_condition,
        "Limit": limit,
        "ScanIndexForward": False,
    }
    if action:
        kwargs["FilterExpression"] = Attr(AuditEventRecord.ACTION).eq(action)
    if exclusive_start_key:
        kwargs["ExclusiveStartKey"] = exclusive_start_key

    response = table.query(**kwargs)
    return response.get("Items", []), response.get("LastEvaluatedKey")


def _query_by_action(
    table: Any,
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

    kwargs: dict[str, Any] = {
        "IndexName": "action-timestamp-index",
        "KeyConditionExpression": key_condition,
        "Limit": limit,
        "ScanIndexForward": False,
    }
    if exclusive_start_key:
        kwargs["ExclusiveStartKey"] = exclusive_start_key

    response = table.query(**kwargs)
    return response.get("Items", []), response.get("LastEvaluatedKey")
