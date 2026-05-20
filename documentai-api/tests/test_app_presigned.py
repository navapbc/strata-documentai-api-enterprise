"""Tests for presigned URL endpoints."""

import pytest

from documentai_api.config.constants import ProcessStatus, UploadMethod


@pytest.fixture(autouse=True)
def _disable_auth(disable_auth):
    pass


def test_create_presigned_url_success(api_client, mocker):
    """Test successful presigned URL generation."""
    mock_insert = mocker.patch("documentai_api.app_presigned.insert_minimal_ddb_record")
    mock_generate = mocker.patch("documentai_api.services.s3.generate_presigned_url")
    mock_generate.return_value = "https://s3.amazonaws.com/presigned-url"

    data = {"filename": "test.pdf", "content_type": "application/pdf"}
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 200
    result = response.json()
    assert "uploadUrl" in result
    assert result["method"] == "PUT"
    assert "jobId" in result
    assert result["expiresIn"] == 900
    assert "headers" in result
    assert result["headers"]["Content-Type"] == "application/pdf"
    mock_insert.assert_called_once()
    call_kwargs = mock_insert.call_args.kwargs
    assert call_kwargs["process_status"] == ProcessStatus.PENDING_UPLOAD
    assert call_kwargs["upload_method"] == UploadMethod.PRESIGNED


def test_create_presigned_url_with_category(api_client, mocker):
    """Test presigned URL with document category."""
    mocker.patch("documentai_api.app_presigned.insert_minimal_ddb_record")
    mock_generate = mocker.patch("documentai_api.services.s3.generate_presigned_url")
    mock_generate.return_value = "https://s3.amazonaws.com/presigned-url"

    data = {
        "filename": "test.pdf",
        "content_type": "application/pdf",
        "category": "income",
    }
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 200
    result = response.json()
    assert "x-amz-meta-user-provided-document-category" in result["headers"]
    assert result["headers"]["x-amz-meta-user-provided-document-category"] == "income"


def test_create_presigned_url_with_trace_id(api_client, mocker):
    """Test presigned URL with trace ID."""
    mocker.patch("documentai_api.app_presigned.insert_minimal_ddb_record")
    mock_generate = mocker.patch("documentai_api.services.s3.generate_presigned_url")
    mock_generate.return_value = "https://s3.amazonaws.com/presigned-url"

    data = {"filename": "test.pdf", "content_type": "application/pdf"}
    response = api_client.post(
        "/v1/documents/presigned-url",
        data=data,
        headers={"X-Trace-ID": "trace-123"},
    )

    assert response.status_code == 200
    assert response.headers["X-Trace-ID"] == "trace-123"
    result = response.json()
    assert result["headers"]["x-amz-meta-trace-id"] == "trace-123"


def test_create_presigned_url_unsupported_content_type(api_client):
    """Test presigned URL with unsupported content type."""
    data = {"filename": "test.zip", "content_type": "application/zip"}
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 400
    assert "BDA-native formats" in response.json()["detail"]


def test_create_presigned_url_convertible_type_rejected(api_client):
    """Test presigned URL rejects formats that require conversion."""
    data = {"filename": "photo.heic", "content_type": "image/heic"}
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 400
    assert "BDA-native formats" in response.json()["detail"]
    assert "direct upload endpoint" in response.json()["detail"]


def test_create_presigned_url_missing_filename(api_client):
    """Test presigned URL with missing filename."""
    data = {"content_type": "application/pdf"}
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 422


def test_create_presigned_url_missing_content_type(api_client):
    """Test presigned URL with missing content_type."""
    data = {"filename": "test.pdf"}
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 422


def test_create_presigned_url_s3_error(api_client, mocker):
    """Test presigned URL when S3 service fails."""
    mocker.patch("documentai_api.app_presigned.insert_minimal_ddb_record")
    mock_generate = mocker.patch("documentai_api.services.s3.generate_presigned_url")
    mock_generate.side_effect = Exception("S3 error")

    data = {"filename": "test.pdf", "content_type": "application/pdf"}
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 500
    assert "Failed to generate upload URL" in response.json()["detail"]


def test_create_presigned_url_no_input_location(api_client, mocker):
    """Test presigned URL when input location not configured."""
    mocker.patch(
        "documentai_api.app_presigned.get_aws_config"
    ).return_value.documentai_input_location = None

    data = {"filename": "test.pdf", "content_type": "application/pdf"}
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 500
    assert "Upload location not configured" in response.json()["detail"]
