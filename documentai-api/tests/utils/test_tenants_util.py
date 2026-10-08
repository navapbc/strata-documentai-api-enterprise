"""Tests for tenant utilities and access validation."""

from typing import Any
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from documentai_api.config.constants import ConfigDefaults
from documentai_api.schemas.tenants import TenantRecord
from documentai_api.utils import tenants as tenants_util
from documentai_api.utils.auth import UserContext
from documentai_api.utils.tenant_access import (
    validate_batch_tenant_access,
    validate_build_tenant_access,
    validate_document_tenant_access,
)

# =============================================================================
# Tenant CRUD (moto-backed)
# =============================================================================


def _add_tenant(table: Any, tenant_id: str, display_name: str = "Test", **kwargs: object) -> None:
    item = {
        TenantRecord.TENANT_ID: tenant_id,
        TenantRecord.DISPLAY_NAME: display_name,
        TenantRecord.IS_ACTIVE: kwargs.get("is_active", True),
    }
    if "primary_contact" in kwargs:
        item[TenantRecord.PRIMARY_CONTACT] = kwargs["primary_contact"]
    table.put_item(Item=item)


def test_get_tenant_found(tenants_table):
    _add_tenant(tenants_table, "test-tenant-id", "Tenant Name")
    result = tenants_util.get_tenant("test-tenant-id")
    assert result is not None
    assert result[TenantRecord.TENANT_ID] == "test-tenant-id"


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
        "test-tenant-id", "Tenant Name", primary_contact="admin@tenant.com"
    )

    assert result[TenantRecord.TENANT_ID] == "test-tenant-id"
    assert result[TenantRecord.DISPLAY_NAME] == "Tenant Name"
    assert result[TenantRecord.PRIMARY_CONTACT] == "admin@tenant.com"
    assert result[TenantRecord.IS_ACTIVE] is True
    assert TenantRecord.CREATED_AT in result

    # Verify in DDB
    item = tenants_table.get_item(Key={TenantRecord.TENANT_ID: "test-tenant-id"})["Item"]
    assert item[TenantRecord.DISPLAY_NAME] == "Tenant Name"


def test_create_tenant_already_exists(tenants_table):
    _add_tenant(tenants_table, "test-tenant-id", "Tenant Name")

    with pytest.raises(ValueError, match="already exists"):
        tenants_util.create_tenant("test-tenant-id", "Tenant Name")


def test_update_tenant_success(tenants_table):
    _add_tenant(tenants_table, "test-tenant-id", "Old Name", is_active=True)

    result = tenants_util.update_tenant("test-tenant-id", display_name="New Name")
    assert result[TenantRecord.DISPLAY_NAME] == "New Name"
    assert TenantRecord.UPDATED_AT in result


def test_update_tenant_not_found(tenants_table):
    with pytest.raises(ValueError, match="not found"):
        tenants_util.update_tenant("missing", display_name="X")


def test_update_tenant_no_fields(tenants_table):
    _add_tenant(tenants_table, "test-tenant-id", "Tenant Name")

    with pytest.raises(ValueError, match="No fields to update"):
        tenants_util.update_tenant("test-tenant-id")


def test_update_tenant_disabled_blueprint_list_set(tenants_table):
    _add_tenant(tenants_table, "test-tenant-id")
    result = tenants_util.update_tenant("test-tenant-id", disabled_blueprint_list=["w2", "1099"])
    assert result[TenantRecord.DISABLED_BLUEPRINT_LIST] == ["w2", "1099"]


def test_update_tenant_disabled_blueprint_list_cleared(tenants_table):
    _add_tenant(tenants_table, "test-tenant-id")
    tenants_util.update_tenant("test-tenant-id", disabled_blueprint_list=["w2"])
    result = tenants_util.update_tenant("test-tenant-id", clear_fields={"disabled_blueprint_list"})
    assert TenantRecord.DISABLED_BLUEPRINT_LIST not in result


def test_update_tenant_disabled_blueprint_list_omitted_leaves_unchanged(tenants_table):
    _add_tenant(tenants_table, "test-tenant-id")
    tenants_util.update_tenant("test-tenant-id", disabled_blueprint_list=["w2"])
    result = tenants_util.update_tenant("test-tenant-id", display_name="Updated")
    assert result[TenantRecord.DISABLED_BLUEPRINT_LIST] == ["w2"]


def test_deactivate_tenant_success(tenants_table):
    _add_tenant(tenants_table, "test-tenant-id", "Tenant Name", is_active=True)
    assert tenants_util.deactivate_tenant("test-tenant-id") is True

    # Verify in DDB
    item = tenants_table.get_item(Key={TenantRecord.TENANT_ID: "test-tenant-id"})["Item"]
    assert item[TenantRecord.IS_ACTIVE] is False


def test_deactivate_tenant_not_found(tenants_table):
    assert tenants_util.deactivate_tenant("missing") is False


# =============================================================================
# Extraction confidence floor
# =============================================================================


def test_confidence_floor_uses_tenant_override(tenants_table):
    _add_tenant(tenants_table, "test-tenant-id", "Tenant Name")
    tenants_util.update_tenant("test-tenant-id", extraction_confidence_floor=0.9)

    assert tenants_util.get_extraction_confidence_floor("test-tenant-id") == 0.9


def test_confidence_floor_falls_back_to_default_when_unset(tenants_table):
    _add_tenant(tenants_table, "test-tenant-id", "Tenant Name")

    assert (
        tenants_util.get_extraction_confidence_floor("test-tenant-id")
        == ConfigDefaults.FIELD_CONFIDENCE_THRESHOLD
    )


def test_confidence_floor_falls_back_to_default_for_missing_tenant(tenants_table):
    assert (
        tenants_util.get_extraction_confidence_floor("missing")
        == ConfigDefaults.FIELD_CONFIDENCE_THRESHOLD
    )


def test_confidence_floor_falls_back_to_default_for_none_tenant(tenants_table):
    assert (
        tenants_util.get_extraction_confidence_floor(None)
        == ConfigDefaults.FIELD_CONFIDENCE_THRESHOLD
    )


# =============================================================================
# Tenant access validation
# =============================================================================


def test_document_tenant_access_passes_when_tenant_matches():
    record = {"tenantId": "test-tenant-id", "fileName": "test.pdf"}
    validate_document_tenant_access(record, "test-tenant-id", "test-job-id")


def test_document_tenant_access_raises_404_when_tenant_mismatches():
    record = {"tenantId": "test-tenant-id", "fileName": "test.pdf"}
    with pytest.raises(HTTPException) as exc_info:
        validate_document_tenant_access(record, "other-tenant", "test-job-id")
    assert exc_info.value.status_code == 404


def test_document_tenant_access_raises_404_when_record_is_none():
    with pytest.raises(HTTPException) as exc_info:
        validate_document_tenant_access(None, "test-tenant-id", "test-job-id")
    assert exc_info.value.status_code == 404


def test_document_tenant_access_raises_404_when_record_has_no_tenant_id():
    record = {"fileName": "test.pdf"}
    with pytest.raises(HTTPException) as exc_info:
        validate_document_tenant_access(record, "test-tenant-id", "test-job-id")
    assert exc_info.value.status_code == 404


def test_document_tenant_access_does_not_reveal_resource_existence():
    """Both 'not found' and 'wrong tenant' return the same 404 message."""
    record = {"tenantId": "test-tenant-id", "fileName": "test.pdf"}

    with pytest.raises(HTTPException) as wrong_tenant:
        validate_document_tenant_access(record, "other-tenant", "test-job-id")

    with pytest.raises(HTTPException) as not_found:
        validate_document_tenant_access(None, "other-tenant", "test-job-id")

    assert wrong_tenant.value.detail == not_found.value.detail


def test_batch_tenant_access_passes_when_tenant_matches():
    auth = UserContext(tenant_id="test-tenant-id", api_key_name="client-1")
    with patch("documentai_api.utils.tenant_access.get_batch") as mock_get:
        mock_get.return_value = {"batchId": "batch-1", "tenantId": "test-tenant-id"}
        validate_batch_tenant_access("batch-1", auth)


def test_batch_tenant_access_raises_404_when_tenant_mismatches():
    auth = UserContext(tenant_id="other-tenant", api_key_name="client-1")
    with patch("documentai_api.utils.tenant_access.get_batch") as mock_get:
        mock_get.return_value = {"batchId": "batch-1", "tenantId": "test-tenant-id"}
        with pytest.raises(HTTPException) as exc_info:
            validate_batch_tenant_access("batch-1", auth)
        assert exc_info.value.status_code == 404


def test_batch_tenant_access_raises_404_when_batch_not_found():
    auth = UserContext(tenant_id="test-tenant-id", api_key_name="client-1")
    with patch("documentai_api.utils.tenant_access.get_batch") as mock_get:
        mock_get.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            validate_batch_tenant_access("batch-missing", auth)
        assert exc_info.value.status_code == 404


def test_batch_tenant_access_raises_404_when_batch_has_no_tenant_id():
    auth = UserContext(tenant_id="test-tenant-id", api_key_name="client-1")
    with patch("documentai_api.utils.tenant_access.get_batch") as mock_get:
        mock_get.return_value = {"batchId": "batch-1"}
        with pytest.raises(HTTPException) as exc_info:
            validate_batch_tenant_access("batch-1", auth)
        assert exc_info.value.status_code == 404


def test_build_tenant_access_passes_when_tenant_matches():
    auth = UserContext(tenant_id="test-tenant-id", api_key_name="client-1")
    with patch("documentai_api.utils.tenant_access.get_build_metadata") as mock_get:
        mock_get.return_value = {"buildId": "build-1", "tenantId": "test-tenant-id"}
        validate_build_tenant_access("build-1", auth)


def test_build_tenant_access_raises_404_when_tenant_mismatches():
    auth = UserContext(tenant_id="other-tenant", api_key_name="client-1")
    with patch("documentai_api.utils.tenant_access.get_build_metadata") as mock_get:
        mock_get.return_value = {"buildId": "build-1", "tenantId": "test-tenant-id"}
        with pytest.raises(HTTPException) as exc_info:
            validate_build_tenant_access("build-1", auth)
        assert exc_info.value.status_code == 404


def test_build_tenant_access_raises_404_when_build_not_found():
    auth = UserContext(tenant_id="test-tenant-id", api_key_name="client-1")
    with patch("documentai_api.utils.tenant_access.get_build_metadata") as mock_get:
        mock_get.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            validate_build_tenant_access("build-missing", auth)
        assert exc_info.value.status_code == 404


def test_build_tenant_access_raises_404_when_build_has_no_tenant_id():
    auth = UserContext(tenant_id="test-tenant-id", api_key_name="client-1")
    with patch("documentai_api.utils.tenant_access.get_build_metadata") as mock_get:
        mock_get.return_value = {"buildId": "build-1"}
        with pytest.raises(HTTPException) as exc_info:
            validate_build_tenant_access("build-1", auth)
        assert exc_info.value.status_code == 404
