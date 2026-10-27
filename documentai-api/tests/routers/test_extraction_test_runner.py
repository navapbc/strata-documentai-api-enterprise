"""Tests for GET /v1/admin/extraction-test endpoints."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from documentai_api.constants.defaults import SystemDefaults
from documentai_api.constants.processing import ProcessStatus
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.jobs import JobStatus
from tests.helpers.fixtures.claims import (
    SUPER_ADMIN_CLAIMS,
    TENANT_ADMIN_CLAIMS,
    TENANT_ADMIN_ID,
    override_jwt,
)

BASE_URL = "/v1/admin/extraction-test"
OTHER_TENANT_ID = "other-tenant-id"


@pytest.fixture(autouse=True)
def _disable_auth(disable_auth):
    pass


@pytest.fixture(autouse=True)
def _bypass_write_limit(mocker):
    mocker.patch("documentai_api.routers.documents.increment_and_check")


def _make_job_status(
    *,
    job_id: str = "test-job-id",
    tenant_id: str = TENANT_ADMIN_ID,
    process_status: str = ProcessStatus.SUCCESS.value,
    v1_response_json: str | None = None,
    object_key: str | None = "tenant/file.pdf",
) -> JobStatus:
    ddb_record = {
        DocumentMetadata.JOB_ID: job_id,
        DocumentMetadata.TENANT_ID: tenant_id,
        DocumentMetadata.PROCESS_STATUS: process_status,
    }
    return JobStatus(
        ddb_record=ddb_record,
        object_key=object_key,
        process_status=process_status,
        v1_response_json=v1_response_json,
    )


##############################################################################
# GET /{job_id} — tenant scoping
##############################################################################


def test_get_unknown_job_returns_404(api_client):
    override_jwt(SUPER_ADMIN_CLAIMS)
    with patch(
        "documentai_api.routers.extraction_test_runner.get_job_status",
        return_value=JobStatus(
            ddb_record=None, object_key=None, process_status=None, v1_response_json=None
        ),
    ):
        response = api_client.get(f"{BASE_URL}/nonexistent-job")
    assert response.status_code == 404


def test_get_cross_tenant_returns_404_for_tenant_admin(api_client):
    """Tenant-admin cannot read a job belonging to another tenant."""
    override_jwt(TENANT_ADMIN_CLAIMS)
    job = _make_job_status(tenant_id=OTHER_TENANT_ID)
    with patch(
        "documentai_api.routers.extraction_test_runner.get_job_status",
        return_value=job,
    ):
        response = api_client.get(f"{BASE_URL}/test-job-id")
    assert response.status_code == 404


def test_get_super_admin_can_read_any_tenant(api_client):
    """Super-admin is not scoped and can read any tenant's job."""
    override_jwt(SUPER_ADMIN_CLAIMS)
    v1 = json.dumps(
        {"jobId": "test-job-id", "jobStatus": ProcessStatus.SUCCESS.value, "message": ""}
    )
    job = _make_job_status(tenant_id=OTHER_TENANT_ID, v1_response_json=v1)
    with patch(
        "documentai_api.routers.extraction_test_runner.get_job_status",
        return_value=job,
    ):
        response = api_client.get(f"{BASE_URL}/test-job-id")
    assert response.status_code == 200


def test_get_tenant_admin_can_read_own_job(api_client):
    override_jwt(TENANT_ADMIN_CLAIMS)
    v1 = json.dumps(
        {"jobId": "test-job-id", "jobStatus": ProcessStatus.SUCCESS.value, "message": ""}
    )
    job = _make_job_status(tenant_id=TENANT_ADMIN_ID, v1_response_json=v1)
    with patch(
        "documentai_api.routers.extraction_test_runner.get_job_status",
        return_value=job,
    ):
        response = api_client.get(f"{BASE_URL}/test-job-id")
    assert response.status_code == 200
    assert response.json()["isCompleted"] is True
    assert response.json()["isFailed"] is False


##############################################################################
# GET /{job_id} — pending / in-progress response
##############################################################################


def test_get_pending_job_returns_not_started(api_client):
    override_jwt(SUPER_ADMIN_CLAIMS)
    job = _make_job_status(process_status=ProcessStatus.NOT_STARTED.value, v1_response_json=None)
    with patch(
        "documentai_api.routers.extraction_test_runner.get_job_status",
        return_value=job,
    ):
        response = api_client.get(f"{BASE_URL}/test-job-id")
    assert response.status_code == 200
    data = response.json()
    assert data["jobStatus"] == ProcessStatus.NOT_STARTED.value
    assert data["isCompleted"] is False
    assert data["isFailed"] is False


##############################################################################
# GET /{job_id} — include_extracted_data
##############################################################################


def test_get_with_include_extracted_data(api_client, mocker):
    override_jwt(SUPER_ADMIN_CLAIMS)
    v1 = {
        "jobId": "test-job-id",
        "jobStatus": ProcessStatus.SUCCESS.value,
        "message": "",
        "fields": {"name": {"value": "Alice", "confidence": 0.99}},
    }
    job = _make_job_status(v1_response_json=json.dumps(v1))
    mock_build = mocker.patch(
        "documentai_api.routers.extraction_test_runner.build_v1_api_response",
        return_value=v1,
    )
    with patch(
        "documentai_api.routers.extraction_test_runner.get_job_status",
        return_value=job,
    ):
        response = api_client.get(f"{BASE_URL}/test-job-id?include_extracted_data=true")
    assert response.status_code == 200
    mock_build.assert_called_once_with(
        object_key=job.object_key,
        job_status=job.process_status,
        include_extracted_data=True,
    )


##############################################################################
# POST — quota and TTL
##############################################################################


def test_post_does_not_increment_quota(api_client, blank_pdf_bytes, mocker):
    """Test runs must not count against the tenant's request quota."""
    mock_increment = mocker.patch("documentai_api.routers.documents.increment_and_check")
    mocker.patch("documentai_api.routers.documents.insert_minimal_ddb_record")
    mocker.patch("documentai_api.routers.documents.dispatch_upload", new_callable=AsyncMock)
    override_jwt(SUPER_ADMIN_CLAIMS)

    api_client.post(
        BASE_URL,
        files={"file": ("test.pdf", blank_pdf_bytes, "application/pdf")},
        data={"tenant_id": TENANT_ADMIN_ID},
    )

    mock_increment.assert_not_called()


def test_post_sets_test_run_ttl(api_client, blank_pdf_bytes, mocker):
    mock_insert = mocker.patch("documentai_api.routers.documents.insert_minimal_ddb_record")
    mocker.patch("documentai_api.routers.documents.dispatch_upload", new_callable=AsyncMock)
    override_jwt(SUPER_ADMIN_CLAIMS)

    api_client.post(
        BASE_URL,
        files={"file": ("test.pdf", blank_pdf_bytes, "application/pdf")},
        data={"tenant_id": TENANT_ADMIN_ID},
    )

    record = mock_insert.call_args[0][0]
    assert record.is_test_run is True
    assert record.ttl_days == SystemDefaults.TEST_RUN_DOCUMENT_TTL_DAYS
