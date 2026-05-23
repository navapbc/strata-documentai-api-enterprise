"""Tests for tenant utilities and access validation."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from documentai_api.schemas.tenants import TenantRecord
from documentai_api.utils import tenants as tenants_util
from documentai_api.utils.auth import UserContext
from documentai_api.utils.tenant import (
    validate_batch_tenant_access,
    validate_build_tenant_access,
    validate_document_tenant_access,
)

# =============================================================================
# Tenant CRUD (moto-backed)
# =============================================================================


def _add_tenant(table, tenant_id: str, display_name: str = "Test", **kwargs):
    item = {
        TenantRecord.TENANT_ID: tenant_id,
        TenantRecord.DISPLAY_NAME: display_name,
        TenantRecord.IS_ACTIVE: kwargs.get("is_active", True),
    }
    if "primary_contact" in kwargs:
        item[TenantRecord.PRIMARY_CONTACT] = kwargs["primary_contact"]
    table.put_item(Item=item)


def test_get_tenant_found(tenants_table):
    _add_tenant(tenants_table, "tenant-a", "Tenant Corp")
    result = tenants_util.get_tenant("tenant-a")
    assert result is not None
    assert result[TenantRecord.TENANT_ID] == "tenant-a"


def test_get_tenant_not_found(tenants_table):
    assert tenants_util.get_tenant("missing") is None


def test_list_tenants_active_only(tenants_table):
    _add_tenant(tenants_table, "a", "A", is_active=True)
    _add_tenant(tenants_table, "b", "B", is_active=False)

    result = tenants_util.list_tenants(active_only=True)
    assert len(result) == 1
    assert result[0][TenantRecord.TENANT_ID] == "a"


def test_list_tenants_all(tenants_table):
    _add_tenant(tenants_table, "a", "A", is_active=True)
    _add_tenant(tenants_table, "b", "B", is_active=False)

    result = tenants_util.list_tenants(active_only=False)
    assert len(result) == 2


def test_create_tenant_success(tenants_table):
    result = tenants_util.create_tenant(
        "tenant-a", "Tenant Corp", primary_contact="admin@tenant.com"
    )

    assert result[TenantRecord.TENANT_ID] == "tenant-a"
    assert result[TenantRecord.DISPLAY_NAME] == "Tenant Corp"
    assert result[TenantRecord.PRIMARY_CONTACT] == "admin@tenant.com"
    assert result[TenantRecord.IS_ACTIVE] is True
    assert TenantRecord.CREATED_AT in result

    # Verify in DDB
    item = tenants_table.get_item(Key={TenantRecord.TENANT_ID: "tenant-a"})["Item"]
    assert item[TenantRecord.DISPLAY_NAME] == "Tenant Corp"


def test_create_tenant_already_exists(tenants_table):
    _add_tenant(tenants_table, "tenant-a", "Tenant Corp")

    with pytest.raises(ValueError, match="already exists"):
        tenants_util.create_tenant("tenant-a", "Tenant Corp")


def test_update_tenant_success(tenants_table):
    _add_tenant(tenants_table, "tenant-a", "Old Name", is_active=True)

    result = tenants_util.update_tenant("tenant-a", display_name="New Name")
    assert result[TenantRecord.DISPLAY_NAME] == "New Name"
    assert TenantRecord.UPDATED_AT in result


def test_update_tenant_not_found(tenants_table):
    with pytest.raises(ValueError, match="not found"):
        tenants_util.update_tenant("missing", display_name="X")


def test_update_tenant_no_fields(tenants_table):
    _add_tenant(tenants_table, "tenant-a", "Tenant Corp")

    with pytest.raises(ValueError, match="No fields to update"):
        tenants_util.update_tenant("tenant-a")


def test_deactivate_tenant_success(tenants_table):
    _add_tenant(tenants_table, "tenant-a", "Tenant Corp", is_active=True)
    assert tenants_util.deactivate_tenant("tenant-a") is True

    # Verify in DDB
    item = tenants_table.get_item(Key={TenantRecord.TENANT_ID: "tenant-a"})["Item"]
    assert item[TenantRecord.IS_ACTIVE] is False


def test_deactivate_tenant_not_found(tenants_table):
    assert tenants_util.deactivate_tenant("missing") is False


# =============================================================================
# Tenant access validation
# =============================================================================


def test_document_tenant_access_passes_when_tenant_matches():
    record = {"tenantId": "tenant-a", "fileName": "test.pdf"}
    validate_document_tenant_access(record, "tenant-a", "job-123")


def test_document_tenant_access_raises_404_when_tenant_mismatches():
    record = {"tenantId": "tenant-a", "fileName": "test.pdf"}
    with pytest.raises(HTTPException) as exc_info:
        validate_document_tenant_access(record, "tenant-b", "job-123")
    assert exc_info.value.status_code == 404


def test_document_tenant_access_raises_404_when_record_is_none():
    with pytest.raises(HTTPException) as exc_info:
        validate_document_tenant_access(None, "tenant-a", "job-123")
    assert exc_info.value.status_code == 404


def test_document_tenant_access_raises_404_when_record_has_no_tenant_id():
    record = {"fileName": "test.pdf"}
    with pytest.raises(HTTPException) as exc_info:
        validate_document_tenant_access(record, "tenant-a", "job-123")
    assert exc_info.value.status_code == 404


def test_document_tenant_access_does_not_reveal_resource_existence():
    """Both 'not found' and 'wrong tenant' return the same 404 message."""
    record = {"tenantId": "tenant-a", "fileName": "test.pdf"}

    with pytest.raises(HTTPException) as wrong_tenant:
        validate_document_tenant_access(record, "tenant-b", "job-123")

    with pytest.raises(HTTPException) as not_found:
        validate_document_tenant_access(None, "tenant-b", "job-123")

    assert wrong_tenant.value.detail == not_found.value.detail


def test_batch_tenant_access_passes_when_tenant_matches():
    auth = UserContext(tenant_id="tenant-a", client_name="client-1")
    with patch("documentai_api.utils.tenant.get_batch") as mock_get:
        mock_get.return_value = {"batchId": "batch-1", "tenantId": "tenant-a"}
        validate_batch_tenant_access("batch-1", auth)


def test_batch_tenant_access_raises_404_when_tenant_mismatches():
    auth = UserContext(tenant_id="tenant-b", client_name="client-1")
    with patch("documentai_api.utils.tenant.get_batch") as mock_get:
        mock_get.return_value = {"batchId": "batch-1", "tenantId": "tenant-a"}
        with pytest.raises(HTTPException) as exc_info:
            validate_batch_tenant_access("batch-1", auth)
        assert exc_info.value.status_code == 404


def test_batch_tenant_access_raises_404_when_batch_not_found():
    auth = UserContext(tenant_id="tenant-a", client_name="client-1")
    with patch("documentai_api.utils.tenant.get_batch") as mock_get:
        mock_get.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            validate_batch_tenant_access("batch-missing", auth)
        assert exc_info.value.status_code == 404


def test_batch_tenant_access_raises_404_when_batch_has_no_tenant_id():
    auth = UserContext(tenant_id="tenant-a", client_name="client-1")
    with patch("documentai_api.utils.tenant.get_batch") as mock_get:
        mock_get.return_value = {"batchId": "batch-1"}
        with pytest.raises(HTTPException) as exc_info:
            validate_batch_tenant_access("batch-1", auth)
        assert exc_info.value.status_code == 404


def test_build_tenant_access_passes_when_tenant_matches():
    auth = UserContext(tenant_id="tenant-a", client_name="client-1")
    with patch("documentai_api.utils.tenant.get_build_metadata") as mock_get:
        mock_get.return_value = {"buildId": "build-1", "tenantId": "tenant-a"}
        validate_build_tenant_access("build-1", auth)


def test_build_tenant_access_raises_404_when_tenant_mismatches():
    auth = UserContext(tenant_id="tenant-b", client_name="client-1")
    with patch("documentai_api.utils.tenant.get_build_metadata") as mock_get:
        mock_get.return_value = {"buildId": "build-1", "tenantId": "tenant-a"}
        with pytest.raises(HTTPException) as exc_info:
            validate_build_tenant_access("build-1", auth)
        assert exc_info.value.status_code == 404


def test_build_tenant_access_raises_404_when_build_not_found():
    auth = UserContext(tenant_id="tenant-a", client_name="client-1")
    with patch("documentai_api.utils.tenant.get_build_metadata") as mock_get:
        mock_get.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            validate_build_tenant_access("build-missing", auth)
        assert exc_info.value.status_code == 404


def test_build_tenant_access_raises_404_when_build_has_no_tenant_id():
    auth = UserContext(tenant_id="tenant-a", client_name="client-1")
    with patch("documentai_api.utils.tenant.get_build_metadata") as mock_get:
        mock_get.return_value = {"buildId": "build-1"}
        with pytest.raises(HTTPException) as exc_info:
            validate_build_tenant_access("build-1", auth)
        assert exc_info.value.status_code == 404
