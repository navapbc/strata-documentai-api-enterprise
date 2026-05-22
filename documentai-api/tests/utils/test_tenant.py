"""Tests for tenant validation dependencies."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from documentai_api.utils.auth import UserContext
from documentai_api.utils.tenant import (
    validate_batch_tenant_access,
    validate_build_tenant_access,
    validate_document_tenant_access,
)

# =============================================================================
# validate_document_tenant_access
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


# =============================================================================
# validate_batch_tenant_access
# =============================================================================


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


# =============================================================================
# validate_build_tenant_access
# =============================================================================


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
