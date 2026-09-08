"""Tests for pipeline/uploads.py dispatch_upload orchestration."""

import io

import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_dispatch_upload_http_exception_classifies_and_reraises(mocker):
    from documentai_api.pipeline.uploads import dispatch_upload

    mocker.patch(
        "documentai_api.pipeline.uploads.upload_document_for_processing",
        side_effect=HTTPException(status_code=500, detail="S3 error"),
    )
    mock_classify = mocker.patch("documentai_api.pipeline.uploads.classify_as_failed")

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
    from documentai_api.pipeline.uploads import dispatch_upload

    mocker.patch(
        "documentai_api.pipeline.uploads.upload_document_for_processing",
        side_effect=RuntimeError("boom"),
    )
    mock_classify = mocker.patch("documentai_api.pipeline.uploads.classify_as_failed")

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
    from documentai_api.pipeline.uploads import dispatch_upload
    from documentai_api.utils.uploads import ImageConversionError

    mocker.patch(
        "documentai_api.pipeline.uploads.upload_document_for_processing",
        side_effect=ImageConversionError("bad image"),
    )
    mock_classify = mocker.patch("documentai_api.pipeline.uploads.classify_as_conversion_failed")

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
