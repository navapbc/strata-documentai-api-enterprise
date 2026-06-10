"""Tests for utils/uploads.py helper functions."""

import io

import pytest
from fastapi import HTTPException, UploadFile

from documentai_api.utils.uploads import generate_unique_filename


def test_generate_unique_filename_simple():
    result = generate_unique_filename("report.pdf", "test-job-id")
    assert result == "report-test-job-id.pdf"


def test_generate_unique_filename_multi_dot():
    result = generate_unique_filename("report.v2.final.pdf", "test-job-id")
    assert result == "report.v2.final-test-job-id.pdf"


def test_generate_unique_filename_no_extension():
    result = generate_unique_filename("README", "test-job-id")
    assert result == "README-test-job-id"


def test_generate_unique_filename_empty_raises():
    with pytest.raises(ValueError, match="Invalid filename"):
        generate_unique_filename("", "test-job-id")


def test_generate_unique_filename_strips_path():
    result = generate_unique_filename("../../foo.pdf", "test-job-id")
    assert result == "foo-test-job-id.pdf"


@pytest.mark.asyncio
async def test_validate_file_type_supported(runtime_required_env, blank_pdf_bytes):
    from documentai_api.utils.uploads import validate_file_type

    file = UploadFile(filename="test.pdf", file=io.BytesIO(blank_pdf_bytes))
    content_type = await validate_file_type(file)
    assert content_type == "application/pdf"


@pytest.mark.asyncio
async def test_validate_file_type_unsupported(runtime_required_env, empty_zip_bytes):
    from documentai_api.utils.uploads import validate_file_type

    file = UploadFile(filename="test.zip", file=io.BytesIO(empty_zip_bytes))
    with pytest.raises(HTTPException) as exc_info:
        await validate_file_type(file)
    assert exc_info.value.status_code == 400
    assert "Invalid file type" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_file_type_resets_pointer(runtime_required_env, blank_pdf_bytes):
    """Verify the file pointer is reset after validation."""
    from documentai_api.utils.uploads import validate_file_type

    file = UploadFile(filename="test.pdf", file=io.BytesIO(blank_pdf_bytes))
    await validate_file_type(file)
    content = await file.read()
    assert len(content) == len(blank_pdf_bytes)


@pytest.mark.asyncio
async def test_validate_upload_missing_filename(runtime_required_env):
    from documentai_api.utils.uploads import validate_upload

    file = UploadFile(filename="", file=io.BytesIO(b"fake"))
    with pytest.raises(HTTPException) as exc_info:
        await validate_upload(file)
    assert exc_info.value.status_code == 400
    assert "Filename is required" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_upload_mime_mismatch_logs_warning(
    runtime_required_env, blank_pdf_bytes, caplog
):
    """Test that MIME mismatch between declared and detected types logs a warning."""
    import logging

    from documentai_api.utils.uploads import validate_upload

    file = UploadFile(
        filename="test.pdf",
        file=io.BytesIO(blank_pdf_bytes),
        headers={"content-type": "image/jpeg"},
    )

    with caplog.at_level(logging.WARNING, logger="documentai_api.utils.uploads"):
        await validate_upload(file)

    assert "MIME mismatch" in caplog.text


@pytest.mark.asyncio
async def test_dispatch_upload_http_exception_classifies_and_reraises(mocker):
    from documentai_api.utils.uploads import dispatch_upload

    mocker.patch(
        "documentai_api.utils.uploads.upload_document_for_processing",
        side_effect=HTTPException(status_code=500, detail="S3 error"),
    )
    mock_classify = mocker.patch("documentai_api.utils.ddb.classify_as_failed")

    with pytest.raises(HTTPException) as exc_info:
        await dispatch_upload(
            src_file=io.BytesIO(b"data"),
            dest_path="s3://bucket/key",
            original_file_name="test.pdf",
            content_type="application/pdf",
            category=None,
            job_id="job-1",
            trace_id="trace-1",
            ddb_key="test-job-1.pdf",
        )

    assert exc_info.value.status_code == 500
    mock_classify.assert_called_once()


@pytest.mark.asyncio
async def test_dispatch_upload_generic_exception_classifies_and_raises_500(mocker):
    from documentai_api.utils.uploads import dispatch_upload

    mocker.patch(
        "documentai_api.utils.uploads.upload_document_for_processing",
        side_effect=RuntimeError("boom"),
    )
    mock_classify = mocker.patch("documentai_api.utils.ddb.classify_as_failed")

    with pytest.raises(HTTPException) as exc_info:
        await dispatch_upload(
            src_file=io.BytesIO(b"data"),
            dest_path="s3://bucket/key",
            original_file_name="test.pdf",
            content_type="application/pdf",
            category=None,
            job_id="job-1",
            trace_id="trace-1",
            ddb_key="test-job-1.pdf",
        )

    assert exc_info.value.status_code == 500
    mock_classify.assert_called_once()


@pytest.mark.asyncio
async def test_dispatch_upload_conversion_error_classifies_and_reraises(mocker):
    from documentai_api.utils.uploads import ImageConversionError, dispatch_upload

    mocker.patch(
        "documentai_api.utils.uploads.upload_document_for_processing",
        side_effect=ImageConversionError("bad image"),
    )
    mock_classify = mocker.patch("documentai_api.utils.ddb.classify_as_conversion_failed")

    with pytest.raises(ImageConversionError):
        await dispatch_upload(
            src_file=io.BytesIO(b"data"),
            dest_path="s3://bucket/key",
            original_file_name="test.pdf",
            content_type="application/pdf",
            category=None,
            job_id="job-1",
            trace_id="trace-1",
            ddb_key="test-job-1.pdf",
        )

    mock_classify.assert_called_once()


def test_save_original_to_preprocessing_tenant_scoped(mocker, monkeypatch):
    """The upload-time original is stored under the tenant's preprocessing prefix."""
    from documentai_api.config.env import EnvVars
    from documentai_api.utils.uploads import _save_original_to_preprocessing

    monkeypatch.setenv(EnvVars.DOCUMENTAI_PREPROCESSING_LOCATION, "s3://bucket/preprocessing")
    mock_upload = mocker.patch("documentai_api.services.s3.upload_file")

    _save_original_to_preprocessing(b"data", "doc-uuid.png", "image/png", tenant_id="test-tenant")

    assert mock_upload.call_args.args[0] == "bucket"
    assert mock_upload.call_args.args[1] == "preprocessing/test-tenant/doc-uuid.png"


def test_save_original_to_preprocessing_without_tenant_falls_back(mocker, monkeypatch):
    """No tenant_id keeps the legacy un-scoped key (e.g. document-build flow)."""
    from documentai_api.config.env import EnvVars
    from documentai_api.utils.uploads import _save_original_to_preprocessing

    monkeypatch.setenv(EnvVars.DOCUMENTAI_PREPROCESSING_LOCATION, "s3://bucket/preprocessing")
    mock_upload = mocker.patch("documentai_api.services.s3.upload_file")

    _save_original_to_preprocessing(b"data", "doc-uuid.png", "image/png")

    assert mock_upload.call_args.args[1] == "preprocessing/doc-uuid.png"
