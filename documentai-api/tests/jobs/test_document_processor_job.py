"""Tests for jobs/document_processor/main.py."""

import pytest

from documentai_api.config.constants import ProcessStatus
from documentai_api.jobs.document_processor.main import (
    invoke_bda,
    main,
)
from documentai_api.schemas.document_metadata import DocumentMetadata


@pytest.fixture(autouse=True)
def disable_tenacity_wait_auto(disable_tenacity_wait):
    pass


@pytest.fixture(autouse=True)
def mock_env(runtime_required_env):
    pass


@pytest.fixture(autouse=True)
def mock_preclassification(mocker):
    from documentai_api.utils.dto import BedrockClassificationResult

    mocker.patch("documentai_api.utils.ddb.get_bda_percentage", return_value=1.0)
    mocker.patch(
        "documentai_api.utils.ddb.preclassify_document",
        return_value=BedrockClassificationResult(
            document_type="tax_documents",
            confidence=0.95,
            document_count=1,
            is_document=True,
            is_blurry=False,
        ),
    )


@pytest.fixture(autouse=True)
def mock_invoke(mocker):
    return mocker.patch("documentai_api.jobs.document_processor.main.invoke_bda")


@pytest.fixture(autouse=True)
def mock_detect_bbox(mocker):
    """Patch detection to a no-op so the crop step in main() never reaches Bedrock.

    Cropping lives in utils.image_optimization; returning None there makes
    crop_image_to_document_roi a no-op during these flow tests.
    """
    return mocker.patch(
        "documentai_api.utils.image_optimization.detect_document_bbox", return_value=None
    )


@pytest.fixture
def input_image(s3_bucket):
    return s3_bucket.put_object(
        Key="input/test.jpg",
        Body=b"image data",
        ContentType="image/jpeg",
        Metadata={
            "job-id": "test-job-id",
            "trace-id": "test-trace-id",
            "user-provided-document-category": "income",
            "original-file-name": "original.jpg",
        },
    )


@pytest.fixture
def input_pdf(s3_bucket):
    return s3_bucket.put_object(
        Key="input/test.pdf",
        Body=b"PDF data",
        ContentType="application/pdf",
        Metadata={
            "job-id": "test-job-id",
            "trace-id": "test-trace-id",
            "user-provided-document-category": "income",
            "original-file-name": "original.pdf",
        },
    )


def test_invoke_bda_success(input_pdf, mocker):
    """Test successful BDA invocation."""
    mock_set_status = mocker.patch(
        "documentai_api.jobs.document_processor.main.set_bda_processing_status_started"
    )

    mock_low_level_invoke = mocker.patch(
        "documentai_api.jobs.document_processor.main.invoke_bedrock_data_automation"
    )
    mock_low_level_invoke.return_value = (
        "arn:aws:bedrock:us-east-1:123456789012:job/abc123",
        "arn:aws:bedrock:us-east-1:123456789012:project/test",
    )

    result = invoke_bda(input_pdf.bucket_name, input_pdf.key, "test.pdf", "tax_documents")

    assert result["invocationArn"] == "arn:aws:bedrock:us-east-1:123456789012:job/abc123"
    mock_set_status.assert_called_once_with(
        object_key="test.pdf",
        bda_invocation_arn="arn:aws:bedrock:us-east-1:123456789012:job/abc123",
        bda_project_arn_used="arn:aws:bedrock:us-east-1:123456789012:project/test",
    )


def test_invoke_bda_failure(input_pdf, mock_invoke, mocker):
    """Test BDA invocation failure updates DDB and raises exception."""
    from botocore.exceptions import ClientError
    from tenacity import RetryError

    mock_classify = mocker.patch("documentai_api.jobs.document_processor.main.classify_as_failed")

    mock_low_level_invoke = mocker.patch(
        "documentai_api.jobs.document_processor.main.invoke_bedrock_data_automation"
    )

    # raise ClientError so retry decorator actually retries
    mock_low_level_invoke.side_effect = ClientError(
        {"Error": {"Code": "ServiceException", "Message": "BDA invocation failed"}},
        "invoke_bedrock_data_automation",
    )

    with pytest.raises(RetryError):
        invoke_bda(input_pdf.bucket_name, input_pdf.key, "test.pdf")

    mock_classify.assert_called_once()
    assert mock_classify.call_args.kwargs["object_key"] == "test.pdf"
    assert mock_classify.call_args.kwargs["error_message"] == "BDA invocation failed"


def test_main_first_time_pdf(input_pdf, mocker, ddb_doc_metadata_table, mock_invoke):
    """Test first time processing PDF (no grayscale needed)."""
    main(input_pdf.key, input_pdf.bucket_name)

    expected_object_key = "test.pdf"

    doc_meta_record = ddb_doc_metadata_table.get_item(Key={"fileName": expected_object_key})["Item"]
    assert doc_meta_record[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.NOT_STARTED

    mock_invoke.assert_called_once_with(
        input_pdf.bucket_name, input_pdf.key, expected_object_key, "tax_documents"
    )


def test_main_strips_tenant_prefix_for_ddb_key(s3_bucket, ddb_doc_metadata_table, mock_invoke):
    """A tenant-prefixed S3 object resolves to a bare (basename) DDB key.

    The API pre-inserts the job record under the un-prefixed filename, so the
    processor must key off the basename to update it in place. S3 operations,
    by contrast, must keep the full tenant-prefixed key.
    """
    tenant_key = "input/test-tenant/document-build-abc.pdf"
    obj = s3_bucket.put_object(
        Key=tenant_key,
        Body=b"PDF data",
        ContentType="application/pdf",
        Metadata={
            "job-id": "test-job-id",
            "trace-id": "test-trace-id",
            "user-provided-document-category": "income",
            "original-file-name": "original.pdf",
        },
    )

    main(obj.key, obj.bucket_name)

    # DDB key is the basename, with the tenant segment stripped.
    expected_ddb_key = "document-build-abc.pdf"
    record = ddb_doc_metadata_table.get_item(Key={"fileName": expected_ddb_key})["Item"]
    assert record[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.NOT_STARTED

    # S3 operations still receive the full tenant-prefixed key.
    mock_invoke.assert_called_once_with(
        obj.bucket_name, tenant_key, expected_ddb_key, "tax_documents"
    )


def test_main_first_time_image(input_image, mocker, ddb_doc_metadata_table, mock_invoke):
    """Test first time processing image (needs grayscale)."""
    mock_convert = mocker.patch(
        "documentai_api.jobs.document_processor.main.convert_s3_object_to_grayscale"
    )
    mock_convert.return_value = True

    main(input_image.key, input_image.bucket_name)

    expected_object_key = "test.jpg"

    doc_meta_record = ddb_doc_metadata_table.get_item(Key={"fileName": expected_object_key})["Item"]
    assert doc_meta_record[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.NOT_STARTED

    mock_convert.assert_called_once_with(input_image.bucket_name, input_image.key)
    mock_invoke.assert_called_once_with(
        input_image.bucket_name, input_image.key, expected_object_key, "tax_documents"
    )


def test_main_grayscale_conversion_fails(input_image, mocker, mock_invoke):
    """Test grayscale conversion failure marks as not implemented."""
    mocker.patch("documentai_api.jobs.document_processor.main.upsert_initial_ddb_record")

    mock_convert = mocker.patch(
        "documentai_api.jobs.document_processor.main.convert_s3_object_to_grayscale"
    )
    mock_convert.return_value = False

    mock_classify = mocker.patch(
        "documentai_api.jobs.document_processor.main.classify_as_not_implemented"
    )

    mock_get = mocker.patch("documentai_api.jobs.document_processor.main.get_ddb_record")
    mock_get.side_effect = [
        None,
        {DocumentMetadata.PROCESS_STATUS: ProcessStatus.PENDING_IMAGE_OPTIMIZATION},
    ]

    main(input_image.key, input_image.bucket_name)

    mock_classify.assert_called_once()
    mock_invoke.assert_not_called()


def test_main_already_processed(input_pdf, mocker, mock_invoke):
    """Test that already processed files are skipped."""
    mock_get = mocker.patch("documentai_api.jobs.document_processor.main.get_ddb_record")
    mock_get.return_value = {DocumentMetadata.PROCESS_STATUS: ProcessStatus.SUCCESS.value}

    main(input_pdf.key, input_pdf.bucket_name)

    mock_invoke.assert_not_called()


def test_main_uses_env_bucket_when_not_provided(input_pdf, mocker, mock_invoke):
    """Test bucket name defaults to environment variable."""
    main(input_pdf.key)

    mock_invoke.assert_called_once_with(
        input_pdf.bucket_name, input_pdf.key, "test.pdf", "tax_documents"
    )


def test_main_idempotent_on_duplicate_events(input_pdf, mocker, mock_invoke):
    """Test job is idempotent when receiving duplicate S3 events."""
    mock_get = mocker.patch("documentai_api.jobs.document_processor.main.get_ddb_record")
    mock_get.return_value = {DocumentMetadata.PROCESS_STATUS: ProcessStatus.STARTED.value}

    main(input_pdf.key, input_pdf.bucket_name)

    mock_invoke.assert_not_called()


def test_main_propagates_s3_metadata(input_pdf, mocker):
    """Test that job_id, trace_id, and document category are read from S3 metadata."""
    mock_insert = mocker.patch(
        "documentai_api.jobs.document_processor.main.upsert_initial_ddb_record"
    )

    mock_get = mocker.patch("documentai_api.jobs.document_processor.main.get_ddb_record")
    mock_get.side_effect = [
        None,
        {DocumentMetadata.PROCESS_STATUS: ProcessStatus.NOT_STARTED.value},
    ]

    main(input_pdf.key, input_pdf.bucket_name)

    mock_insert.assert_called_once()
    call_kwargs = mock_insert.call_args.kwargs

    assert call_kwargs["job_id"] == "test-job-id"
    assert call_kwargs["trace_id"] == "test-trace-id"
    assert call_kwargs["user_provided_document_category"] == "income"
    assert call_kwargs["original_file_name"] == "original.pdf"
