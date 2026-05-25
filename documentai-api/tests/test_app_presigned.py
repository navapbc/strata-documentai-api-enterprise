"""Tests for presigned URL endpoints."""

import pytest

from documentai_api.config.constants import ProcessStatus, UploadMethod


@pytest.fixture(autouse=True)
def _disable_auth(disable_auth):
    pass


def test_create_presigned_url_success(api_client, mocker):
    """Test successful presigned POST generation."""
    mock_insert = mocker.patch("documentai_api.app_presigned.insert_minimal_ddb_record")
    mock_generate = mocker.patch("documentai_api.services.s3.generate_presigned_post")
    mock_generate.return_value = {
        "url": "https://s3.amazonaws.com/test-bucket",
        "fields": {"key": "input/test.pdf", "Content-Type": "application/pdf"},
    }

    data = {"filename": "test.pdf", "content_type": "application/pdf"}
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 200
    result = response.json()
    assert "uploadUrl" in result
    assert result["method"] == "POST"
    assert "jobId" in result
    assert result["expiresIn"] == 900
    assert "maxSizeBytes" in result
    assert "fields" in result
    assert result["fields"]["Content-Type"] == "application/pdf"
    mock_insert.assert_called_once()
    record = mock_insert.call_args[0][0]
    assert record.process_status == ProcessStatus.PENDING_UPLOAD
    assert record.upload_method == UploadMethod.PRESIGNED


def test_create_presigned_url_with_category(api_client, mocker):
    """Test presigned POST with document category includes metadata in fields."""
    mocker.patch("documentai_api.app_presigned.insert_minimal_ddb_record")
    mock_generate = mocker.patch("documentai_api.services.s3.generate_presigned_post")
    mock_generate.return_value = {
        "url": "https://s3.amazonaws.com/test-bucket",
        "fields": {
            "key": "input/test.pdf",
            "Content-Type": "application/pdf",
            "x-amz-meta-user-provided-document-category": "income",
        },
    }

    data = {
        "filename": "test.pdf",
        "content_type": "application/pdf",
        "category": "income",
    }
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 200
    result = response.json()
    assert result["fields"]["x-amz-meta-user-provided-document-category"] == "income"


def test_create_presigned_url_with_trace_id(api_client, mocker):
    """Test presigned POST echoes valid UUID trace ID."""
    mocker.patch("documentai_api.app_presigned.insert_minimal_ddb_record")
    mock_generate = mocker.patch("documentai_api.services.s3.generate_presigned_post")
    mock_generate.return_value = {
        "url": "https://s3.amazonaws.com/test-bucket",
        "fields": {
            "key": "input/test.pdf",
            "Content-Type": "application/pdf",
            "x-amz-meta-trace-id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        },
    }

    data = {"filename": "test.pdf", "content_type": "application/pdf"}
    response = api_client.post(
        "/v1/documents/presigned-url",
        data=data,
        headers={"X-Trace-ID": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"},
    )

    assert response.status_code == 200
    assert response.headers["X-Trace-ID"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


def test_create_presigned_url_unsupported_content_type(api_client):
    """Test presigned POST with unsupported content type."""
    data = {"filename": "test.zip", "content_type": "application/zip"}
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 400
    assert "BDA-native formats" in response.json()["detail"]


def test_create_presigned_url_convertible_type_rejected(api_client):
    """Test presigned POST rejects formats that require conversion."""
    data = {"filename": "photo.heic", "content_type": "image/heic"}
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 400
    assert "BDA-native formats" in response.json()["detail"]
    assert "direct upload endpoint" in response.json()["detail"]


def test_create_presigned_url_missing_filename(api_client):
    """Test presigned POST with missing filename."""
    data = {"content_type": "application/pdf"}
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 422


def test_create_presigned_url_missing_content_type(api_client):
    """Test presigned POST with missing content_type."""
    data = {"filename": "test.pdf"}
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 422


def test_create_presigned_url_s3_error(api_client, mocker):
    """Test presigned POST when S3 service fails."""
    mocker.patch("documentai_api.app_presigned.insert_minimal_ddb_record")
    mock_generate = mocker.patch("documentai_api.services.s3.generate_presigned_post")
    mock_generate.side_effect = Exception("S3 error")

    data = {"filename": "test.pdf", "content_type": "application/pdf"}
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 500
    assert "Failed to generate upload URL" in response.json()["detail"]


def test_create_presigned_url_no_input_location(api_client, mocker):
    """Test presigned POST when input location not configured."""
    mocker.patch(
        "documentai_api.app_presigned.get_aws_config"
    ).return_value.documentai_input_location = None

    data = {"filename": "test.pdf", "content_type": "application/pdf"}
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 500
    assert "Upload location not configured" in response.json()["detail"]


def test_create_presigned_url_invalid_trace_id_generates_new(api_client, mocker):
    """Non-UUID trace ID is replaced with a generated UUID."""
    import uuid

    mocker.patch("documentai_api.app_presigned.insert_minimal_ddb_record")
    mock_generate = mocker.patch("documentai_api.services.s3.generate_presigned_post")
    mock_generate.return_value = {
        "url": "https://s3.amazonaws.com/test-bucket",
        "fields": {"key": "input/test.pdf", "Content-Type": "application/pdf"},
    }

    data = {"filename": "test.pdf", "content_type": "application/pdf"}
    response = api_client.post(
        "/v1/documents/presigned-url",
        data=data,
        headers={"X-Trace-ID": "not-a-uuid"},
    )

    assert response.status_code == 200
    trace_id = response.headers["X-Trace-ID"]
    assert trace_id != "not-a-uuid"
    uuid.UUID(trace_id)  # valid UUID


def test_create_presigned_url_tenant_in_s3_key(api_client, mocker):
    """S3 key includes tenant_id for isolation."""
    mocker.patch("documentai_api.app_presigned.insert_minimal_ddb_record")
    mock_generate = mocker.patch("documentai_api.services.s3.generate_presigned_post")
    mock_generate.return_value = {
        "url": "https://s3.amazonaws.com/test-bucket",
        "fields": {"key": "input/test.pdf", "Content-Type": "application/pdf"},
    }

    data = {"filename": "test.pdf", "content_type": "application/pdf"}
    api_client.post("/v1/documents/presigned-url", data=data)

    call_kwargs = mock_generate.call_args.kwargs
    # Key should contain the tenant_id (from disable_auth fixture: "test-tenant")
    assert "test-tenant" in call_kwargs["key"]


def test_s3_error_does_not_write_ddb(api_client, mocker):
    """When signing fails, DDB insert must NOT be called (order-of-operations guard)."""
    mock_insert = mocker.patch("documentai_api.app_presigned.insert_minimal_ddb_record")
    mock_generate = mocker.patch("documentai_api.services.s3.generate_presigned_post")
    mock_generate.side_effect = Exception("signing failed")

    data = {"filename": "test.pdf", "content_type": "application/pdf"}
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 500
    mock_insert.assert_not_called()


def test_malformed_input_location(api_client, mocker):
    """Malformed input_location returns 500 with 'misconfigured' detail."""
    mocker.patch(
        "documentai_api.app_presigned.get_aws_config"
    ).return_value.documentai_input_location = "not-an-s3-uri"
    mocker.patch("documentai_api.app_presigned.parse_s3_uri", side_effect=Exception("bad uri"))

    data = {"filename": "test.pdf", "content_type": "application/pdf"}
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 500
    assert "misconfigured" in response.json()["detail"].lower()


def test_max_size_bytes_passed_to_s3(api_client, mocker):
    """max_size_bytes is passed to generate_presigned_post for S3 enforcement."""
    mocker.patch("documentai_api.app_presigned.insert_minimal_ddb_record")
    mock_generate = mocker.patch("documentai_api.services.s3.generate_presigned_post")
    mock_generate.return_value = {
        "url": "https://s3.amazonaws.com/test-bucket",
        "fields": {"key": "input/test.pdf", "Content-Type": "application/pdf"},
    }

    data = {"filename": "test.pdf", "content_type": "application/pdf"}
    api_client.post("/v1/documents/presigned-url", data=data)

    call_kwargs = mock_generate.call_args.kwargs
    assert "max_size_bytes" in call_kwargs
    assert call_kwargs["max_size_bytes"] > 0


def test_filename_length_cap(api_client):
    """Filename exceeding max_length is rejected with 422."""
    data = {"filename": "x" * 300 + ".pdf", "content_type": "application/pdf"}
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 422


def test_external_document_id_invalid_pattern(api_client, mocker):
    """external_document_id with invalid characters is rejected."""
    mocker.patch("documentai_api.app_presigned.insert_minimal_ddb_record")
    mocker.patch(
        "documentai_api.services.s3.generate_presigned_post",
        return_value={
            "url": "https://s3.amazonaws.com/test-bucket",
            "fields": {"key": "input/test.pdf", "Content-Type": "application/pdf"},
        },
    )

    data = {
        "filename": "test.pdf",
        "content_type": "application/pdf",
        "external_document_id": "has spaces and $pecial",
    }
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 422


def test_external_system_id_too_long(api_client, mocker):
    """external_system_id exceeding max_length is rejected."""
    mocker.patch("documentai_api.app_presigned.insert_minimal_ddb_record")
    mocker.patch(
        "documentai_api.services.s3.generate_presigned_post",
        return_value={
            "url": "https://s3.amazonaws.com/test-bucket",
            "fields": {"key": "input/test.pdf", "Content-Type": "application/pdf"},
        },
    )

    data = {
        "filename": "test.pdf",
        "content_type": "application/pdf",
        "external_system_id": "x" * 200,
    }
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 422


def test_non_ascii_filename_sanitized(api_client, mocker):
    """Non-ASCII filename is percent-encoded in S3 metadata."""
    mocker.patch("documentai_api.app_presigned.insert_minimal_ddb_record")
    mock_generate = mocker.patch("documentai_api.services.s3.generate_presigned_post")
    mock_generate.return_value = {
        "url": "https://s3.amazonaws.com/test-bucket",
        "fields": {"key": "input/test.pdf", "Content-Type": "application/pdf"},
    }

    data = {"filename": "日本語ファイル.pdf", "content_type": "application/pdf"}
    api_client.post("/v1/documents/presigned-url", data=data)

    call_kwargs = mock_generate.call_args.kwargs
    metadata = call_kwargs["metadata"]
    # Should be percent-encoded, not raw unicode
    assert "日本語" not in metadata["original-file-name"]
    assert "%E6%97%A5" in metadata["original-file-name"]  # 日 percent-encoded


def test_path_traversal_filename_contained(api_client, mocker):
    """Path traversal in filename doesn't escape tenant prefix in S3 key."""
    mocker.patch("documentai_api.app_presigned.insert_minimal_ddb_record")
    mock_generate = mocker.patch("documentai_api.services.s3.generate_presigned_post")
    mock_generate.return_value = {
        "url": "https://s3.amazonaws.com/test-bucket",
        "fields": {"key": "input/test.pdf", "Content-Type": "application/pdf"},
    }

    data = {"filename": "../../etc/passwd.pdf", "content_type": "application/pdf"}
    api_client.post("/v1/documents/presigned-url", data=data)

    call_kwargs = mock_generate.call_args.kwargs
    s3_key = call_kwargs["key"]
    # Key must contain tenant_id and not have ../ traversal
    assert "test-tenant" in s3_key
    assert "../" not in s3_key


def test_ddb_insert_failure_returns_500(api_client, mocker):
    """When DDB insert fails after signing, returns 500 with clean message."""
    mock_insert = mocker.patch("documentai_api.app_presigned.insert_minimal_ddb_record")
    mock_insert.side_effect = Exception("DDB unavailable")
    mocker.patch(
        "documentai_api.services.s3.generate_presigned_post",
        return_value={
            "url": "https://s3.amazonaws.com/test-bucket",
            "fields": {"key": "input/test.pdf", "Content-Type": "application/pdf"},
        },
    )

    data = {"filename": "test.pdf", "content_type": "application/pdf"}
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 500
    assert "Failed to create upload record" in response.json()["detail"]


def test_success_response_contains_s3_url(api_client, mocker):
    """upload_url in response matches what S3 returned."""
    mocker.patch("documentai_api.app_presigned.insert_minimal_ddb_record")
    mock_generate = mocker.patch("documentai_api.services.s3.generate_presigned_post")
    mock_generate.return_value = {
        "url": "https://my-bucket.s3.amazonaws.com",
        "fields": {"key": "input/test.pdf", "Content-Type": "application/pdf"},
    }

    data = {"filename": "test.pdf", "content_type": "application/pdf"}
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 200
    assert response.json()["uploadUrl"] == "https://my-bucket.s3.amazonaws.com"


def test_success_response_job_id_is_valid_uuid(api_client, mocker):
    """JobId in response is a valid UUID."""
    import uuid

    mocker.patch("documentai_api.app_presigned.insert_minimal_ddb_record")
    mocker.patch(
        "documentai_api.services.s3.generate_presigned_post",
        return_value={
            "url": "https://s3.amazonaws.com/test-bucket",
            "fields": {"key": "input/test.pdf", "Content-Type": "application/pdf"},
        },
    )

    data = {"filename": "test.pdf", "content_type": "application/pdf"}
    response = api_client.post("/v1/documents/presigned-url", data=data)

    assert response.status_code == 200
    uuid.UUID(response.json()["jobId"])


def test_tenant_id_propagated_to_ddb(api_client, mocker):
    """tenant_id from auth is passed to insert_minimal_ddb_record."""
    mock_insert = mocker.patch("documentai_api.app_presigned.insert_minimal_ddb_record")
    mocker.patch(
        "documentai_api.services.s3.generate_presigned_post",
        return_value={
            "url": "https://s3.amazonaws.com/test-bucket",
            "fields": {"key": "input/test.pdf", "Content-Type": "application/pdf"},
        },
    )

    data = {"filename": "test.pdf", "content_type": "application/pdf"}
    api_client.post("/v1/documents/presigned-url", data=data)

    record = mock_insert.call_args[0][0]
    assert record.tenant_id == "test-tenant"
    assert record.api_key_name == "test-client"
