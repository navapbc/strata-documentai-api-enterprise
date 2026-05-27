"""Tests for audit event logging utility."""

from documentai_api.schemas.audit_event import GLOBAL_TENANT, AuditEventRecord
from documentai_api.utils.audit import log_event

CLAIMS = {"sub": "test-user", "email": "admin@example.com"}


def test_log_event_writes_to_ddb(audit_events_table):
    log_event(
        CLAIMS,
        action="tenant.create",
        target_type="tenant",
        target_id="acme",
        metadata={"display_name": "Acme Corp"},
    )

    items = audit_events_table.scan()["Items"]
    # tenant.create has no tenant_id, so only __global__ (no double-write)
    assert len(items) == 1
    item = items[0]
    assert item[AuditEventRecord.TENANT_ID] == GLOBAL_TENANT
    assert item[AuditEventRecord.ACTION] == "tenant.create"
    assert item[AuditEventRecord.TARGET_TYPE] == "tenant"
    assert item[AuditEventRecord.TARGET_ID] == "acme"
    assert item[AuditEventRecord.ACTOR_SUB] == "test-user"
    assert item[AuditEventRecord.ACTOR_EMAIL] == "admin@example.com"
    assert item[AuditEventRecord.METADATA] == {"display_name": "Acme Corp"}
    assert AuditEventRecord.TTL in item


def test_log_event_double_writes_to_global(audit_events_table):
    log_event(
        CLAIMS,
        action="key.create",
        target_type="key",
        target_id="abc12345",
        tenant_id="acme",
    )

    items = audit_events_table.scan()["Items"]
    assert len(items) == 2
    partitions = {i[AuditEventRecord.TENANT_ID] for i in items}
    assert partitions == {"acme", GLOBAL_TENANT}


def test_log_event_uses_tenant_id_as_partition(audit_events_table):
    log_event(
        CLAIMS,
        action="tenant.update",
        target_type="tenant",
        target_id="acme",
        tenant_id="acme",
    )

    items = audit_events_table.scan()["Items"]
    # Double-write: one in "acme", one in __global__
    assert len(items) == 2
    tenant_item = next(i for i in items if i[AuditEventRecord.TENANT_ID] == "acme")
    assert tenant_item[AuditEventRecord.ACTION] == "tenant.update"


def test_log_event_defaults_to_global_tenant(audit_events_table):
    log_event(
        CLAIMS,
        action="key.create",
        target_type="key",
        target_id="abc12345",
    )

    items = audit_events_table.scan()["Items"]
    # No tenant_id means only __global__ (no double-write)
    assert len(items) == 1
    assert items[0][AuditEventRecord.TENANT_ID] == GLOBAL_TENANT


def test_log_event_does_not_raise_on_failure(monkeypatch):
    """Audit logging should never break the request - failures are swallowed."""
    monkeypatch.setenv("AUDIT_EVENTS_TABLE_NAME", "nonexistent-table")
    # implicit: function should not raise
    log_event(
        CLAIMS,
        action="tenant.create",
        target_type="tenant",
        target_id="acme",
    )
