"""Tests for app_blueprint_test.py - POST /test and GET /test/{test_id}."""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from documentai_api.app import app
from documentai_api.config.env import EnvVars
from tests.helpers.fixtures.claims import clear_jwt_override, make_claims, override_jwt

TENANT_ID = "test-tenant"
OTHER_TENANT_ID = "other-tenant"
TEST_URL = "/v1/admin/blueprints/test"
INVOCATION_ARN = "arn:aws:bedrock:us-east-1:123:invocation/abc"
PROJECT_ARN = "arn:aws:bedrock:us-east-1:123:project/all"
PROFILE_ARN = "arn:aws:bedrock:us-east-1:123:profile/default"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    clear_jwt_override()


@pytest.fixture
def base_env(monkeypatch, s3_bucket):
    monkeypatch.setenv(EnvVars.DOCUMENTAI_INPUT_LOCATION, f"s3://{s3_bucket.name}/input")
    monkeypatch.setenv(EnvVars.DOCUMENTAI_OUTPUT_LOCATION, f"s3://{s3_bucket.name}/output")
    monkeypatch.setenv(EnvVars.BDA_PROJECT_ARN_ALL, PROJECT_ARN)
    monkeypatch.setenv(EnvVars.BDA_PROFILE_ARN, PROFILE_ARN)
    return s3_bucket


@pytest.fixture
def mock_invoke_bda(mocker):
    return mocker.patch(
        "documentai_api.app_blueprint_test.invoke_bda_async",
        return_value=INVOCATION_ARN,
    )


@pytest.fixture
def mock_store_metadata(mocker):
    return mocker.patch("documentai_api.app_blueprint_test.store_test_metadata")


@pytest.fixture
def mock_get_metadata(mocker):
    return mocker.patch("documentai_api.app_blueprint_test.get_test_metadata")


@pytest.fixture
def mock_cleanup(mocker):
    return mocker.patch("documentai_api.app_blueprint_test.cleanup_test")


def _upload_file_data(filename: str = "doc.pdf", content: bytes = b"PDF content"):
    return {"file": (filename, BytesIO(content), "application/pdf")}


# =============================================================================
# POST /test - auth
# =============================================================================


def test_start_test_unauthenticated_returns_401(client, base_env):
    response = client.post(
        TEST_URL, files=_upload_file_data(), data={"document_category": "income"}
    )
    assert response.status_code == 401


def test_start_test_non_admin_returns_403(client, base_env):
    override_jwt(make_claims(groups=[]))
    response = client.post(
        TEST_URL, files=_upload_file_data(), data={"document_category": "income"}
    )
    assert response.status_code == 403


# =============================================================================
# POST /test - tenant scoping
# =============================================================================


def test_start_test_tenant_admin_uses_own_tenant(
    client, base_env, mock_invoke_bda, mock_store_metadata
):
    override_jwt(make_claims(groups=["tenant-admin"], tenant_id=TENANT_ID))
    response = client.post(
        TEST_URL, files=_upload_file_data(), data={"document_category": "income"}
    )

    assert response.status_code == 200
    _, _, stored_tenant_id, _, _ = mock_store_metadata.call_args.args
    assert stored_tenant_id == TENANT_ID


def test_start_test_tenant_admin_cannot_use_other_tenant(client, base_env, mock_invoke_bda):
    override_jwt(make_claims(groups=["tenant-admin"], tenant_id=TENANT_ID))
    response = client.post(
        TEST_URL,
        files=_upload_file_data(),
        data={"document_category": "income", "tenant_id": OTHER_TENANT_ID},
    )
    assert response.status_code == 403


def test_start_test_super_admin_requires_tenant_id(client, base_env, mock_invoke_bda):
    override_jwt(make_claims(groups=["super-admin"]))
    response = client.post(
        TEST_URL, files=_upload_file_data(), data={"document_category": "income"}
    )
    assert response.status_code == 400


def test_start_test_super_admin_with_tenant_id_succeeds(
    client, base_env, mock_invoke_bda, mock_store_metadata
):
    override_jwt(make_claims(groups=["super-admin"]))
    response = client.post(
        TEST_URL,
        files=_upload_file_data(),
        data={"document_category": "income", "tenant_id": TENANT_ID},
    )
    assert response.status_code == 200
    data = response.json()
    assert "testId" in data
    assert data["status"] == "PROCESSING"


# =============================================================================
# POST /test - BDA errors
# =============================================================================


def test_start_test_unknown_category_returns_400(client, base_env, mocker):
    override_jwt(make_claims(groups=["tenant-admin"], tenant_id=TENANT_ID))
    mocker.patch(
        "documentai_api.app_blueprint_test.invoke_bda_async",
        side_effect=ValueError("Unknown document category: bogus"),
    )
    response = client.post(TEST_URL, files=_upload_file_data(), data={"document_category": "bogus"})
    assert response.status_code == 400
    assert "Unknown document category" in response.json()["detail"]


# =============================================================================
# GET /test/{test_id} - auth
# =============================================================================


def test_get_result_unauthenticated_returns_401(client, base_env):
    response = client.get(f"{TEST_URL}/some-id")
    assert response.status_code == 401


# =============================================================================
# GET /test/{test_id} - not found
# =============================================================================


def test_get_result_not_found_returns_404(client, base_env, mock_get_metadata):
    override_jwt(make_claims(groups=["tenant-admin"], tenant_id=TENANT_ID))
    mock_get_metadata.return_value = None

    response = client.get(f"{TEST_URL}/missing-id")
    assert response.status_code == 404


# =============================================================================
# GET /test/{test_id} - tenant scoping
# =============================================================================


def test_get_result_tenant_admin_cannot_access_other_tenant(
    client, base_env, mock_get_metadata, mocker
):
    from documentai_api.utils.blueprint_test import BlueprintTestMetadata

    override_jwt(make_claims(groups=["tenant-admin"], tenant_id=TENANT_ID))
    mock_get_metadata.return_value = BlueprintTestMetadata(
        invocation_arn=INVOCATION_ARN,
        tenant_id=OTHER_TENANT_ID,
        document_type="w2",
        test_key="test-runner/abc/doc.pdf",
    )

    response = client.get(f"{TEST_URL}/some-id")
    assert response.status_code == 403


# =============================================================================
# GET /test/{test_id} - BDA status polling
# =============================================================================


def _make_metadata(tenant_id: str = TENANT_ID):
    from documentai_api.utils.blueprint_test import BlueprintTestMetadata

    return BlueprintTestMetadata(
        invocation_arn=INVOCATION_ARN,
        tenant_id=tenant_id,
        document_type="w2",
        test_key="test-runner/abc/doc.pdf",
    )


def test_get_result_returns_processing_when_no_job_response(
    client, base_env, mock_get_metadata, mocker
):
    override_jwt(make_claims(groups=["tenant-admin"], tenant_id=TENANT_ID))
    mock_get_metadata.return_value = _make_metadata()
    mocker.patch("documentai_api.app_blueprint_test.get_bda_job_response", return_value=None)

    response = client.get(f"{TEST_URL}/some-id")
    assert response.status_code == 200
    assert response.json()["status"] == "PROCESSING"


def test_get_result_returns_processing_when_in_progress(
    client, base_env, mock_get_metadata, mocker
):
    override_jwt(make_claims(groups=["tenant-admin"], tenant_id=TENANT_ID))
    mock_get_metadata.return_value = _make_metadata()
    mocker.patch(
        "documentai_api.app_blueprint_test.get_bda_job_response",
        return_value={"status": "InProgress"},
    )

    response = client.get(f"{TEST_URL}/some-id")
    assert response.json()["status"] == "PROCESSING"


def test_get_result_returns_failed_on_bda_failure(
    client, base_env, mock_get_metadata, mock_cleanup, mocker
):
    override_jwt(make_claims(groups=["tenant-admin"], tenant_id=TENANT_ID))
    mock_get_metadata.return_value = _make_metadata()
    mocker.patch(
        "documentai_api.app_blueprint_test.get_bda_job_response",
        return_value={"status": "ServiceError"},
    )

    response = client.get(f"{TEST_URL}/some-id")
    assert response.json()["status"] == "FAILED"
    mock_cleanup.assert_called_once()


def test_get_result_returns_failed_when_no_bda_output(client, base_env, mock_get_metadata, mocker):
    override_jwt(make_claims(groups=["tenant-admin"], tenant_id=TENANT_ID))
    mock_get_metadata.return_value = _make_metadata()
    mocker.patch(
        "documentai_api.app_blueprint_test.get_bda_job_response",
        return_value={
            "status": "Success",
            "outputConfiguration": {"s3Uri": "s3://output-bucket/test-runner/abc/doc.pdf"},
        },
    )
    mocker.patch("documentai_api.app_blueprint_test.extract_bda_output_s3_uri", return_value=None)

    response = client.get(f"{TEST_URL}/some-id")
    assert response.json()["status"] == "FAILED"
    assert "No BDA output" in response.json()["error"]


def test_get_result_returns_failed_when_result_unreadable(
    client, base_env, mock_get_metadata, mocker
):
    override_jwt(make_claims(groups=["tenant-admin"], tenant_id=TENANT_ID))
    mock_get_metadata.return_value = _make_metadata()
    mocker.patch(
        "documentai_api.app_blueprint_test.get_bda_job_response",
        return_value={
            "status": "Success",
            "outputConfiguration": {"s3Uri": "s3://output-bucket/test-runner/abc/doc.pdf"},
        },
    )
    mocker.patch(
        "documentai_api.app_blueprint_test.extract_bda_output_s3_uri",
        return_value="s3://output-bucket/result.json",
    )
    mocker.patch("documentai_api.app_blueprint_test.get_bda_result_json", return_value=None)

    response = client.get(f"{TEST_URL}/some-id")
    assert response.json()["status"] == "FAILED"
    assert "Could not read" in response.json()["error"]


def test_get_result_returns_completed_with_extraction(
    client, base_env, mock_get_metadata, mock_cleanup, mocker
):
    from documentai_api.utils.bda_output_processor import BdaExtractionResult, MatchedBlueprintInfo

    override_jwt(make_claims(groups=["tenant-admin"], tenant_id=TENANT_ID))
    mock_get_metadata.return_value = _make_metadata()
    mocker.patch(
        "documentai_api.app_blueprint_test.get_bda_job_response",
        return_value={
            "status": "Success",
            "outputConfiguration": {"s3Uri": "s3://output-bucket/test-runner/abc/doc.pdf"},
        },
    )
    mocker.patch(
        "documentai_api.app_blueprint_test.extract_bda_output_s3_uri",
        return_value="s3://output-bucket/result.json",
    )
    mocker.patch(
        "documentai_api.app_blueprint_test.get_bda_result_json",
        return_value={"some": "result"},
    )
    mock_extract = mocker.patch(
        "documentai_api.app_blueprint_test.extract_bda_result_from_json",
        return_value=BdaExtractionResult(
            document_type="w2",
            matched_blueprint=MatchedBlueprintInfo(name="W2 Blueprint", confidence=0.95),
            field_values={"employer": "Acme"},
            field_confidences={"employer": 0.95},
            filtered_fields={},
            missing_required=[],
            has_rules=False,
        ),
    )

    response = client.get(f"{TEST_URL}/some-id")
    data = response.json()

    assert data["status"] == "COMPLETED"
    assert data["matchedBlueprint"] == "W2 Blueprint"
    assert data["matchedConfidence"] == 0.95
    assert data["extractedFields"] == {"employer": "Acme"}
    mock_cleanup.assert_called_once()
    mock_extract.assert_called_once_with({"some": "result"}, TENANT_ID, "w2")
