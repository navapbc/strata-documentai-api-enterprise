"""Tests for jobs/document_processor/main.py."""

import time
from decimal import Decimal
from unittest.mock import ANY, Mock

import pytest
from botocore.exceptions import ClientError
from tenacity import RetryError

from documentai_api.config.constants import ProcessStatus
from documentai_api.config.constants_preclassification_category_generated import (
    PreclassificationCategory,
)
from documentai_api.dtos.classification import (
    BedrockClassificationResult,
    PreclassificationMatchResult,
)
from documentai_api.dtos.processing import CropResult, OptimizationResult
from documentai_api.jobs.document_processor.main import (
    _invoke_bda,
    _persist_optimization_metrics,
    _should_invoke_bda,
    invoke_bda,
    main,
)
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.blur_detection import BlurResult

_MAIN_MODULE = "documentai_api.jobs.document_processor.main"
_LIFECYCLE_MODULE = "documentai_api.pipeline.document_lifecycle"


@pytest.fixture(autouse=True)
def disable_tenacity_wait_auto(disable_tenacity_wait):
    pass


@pytest.fixture(autouse=True)
def mock_env(runtime_required_env):
    pass


@pytest.fixture(autouse=True)
def mock_preclassification(mocker):
    mocker.patch(
        f"{_LIFECYCLE_MODULE}.preclassify_document",
        return_value=BedrockClassificationResult(
            document_type="tax_documents",
            confidence=0.95,
            max_document_count_on_page=1,
        ),
    )


@pytest.fixture(autouse=True)
def mock_find_matching_blueprint(mocker):
    mocker.patch(
        f"{_LIFECYCLE_MODULE}.find_matching_blueprint",
        return_value=PreclassificationMatchResult(
            matched_document_type="w2-form",
            confidence=0.95,
            category=PreclassificationCategory.INCOME,
        ),
    )


@pytest.fixture(autouse=True)
def mock_invoke_bda(mocker):
    return mocker.patch("documentai_api.jobs.document_processor.main.invoke_bda")


@pytest.fixture(autouse=True)
def mock_is_selected_for_processing(mocker):
    """Prevent document_categories table lookup. Document is always selected for processing."""
    return mocker.patch(
        "documentai_api.pipeline.document_lifecycle.is_selected_for_processing",
        return_value=(True, None, None),
    )


@pytest.fixture(autouse=True)
def mock_detect_bbox(mocker):
    """Patch detection to a no-op so the crop step never reaches Bedrock."""
    return mocker.patch(
        "documentai_api.utils.image_optimization.detect_document_bbox",
        return_value=(None, CropResult()),
    )


# Minimal leading bytes that filetype.guess_mime detects as the right format.
# The processor now sniffs uploaded content before processing (SEC-HIGH-05), so
# fixtures must carry real magic bytes, not placeholder text.
JPEG_MAGIC = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01"
PDF_MAGIC = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"


@pytest.fixture
def input_image(s3_bucket, ddb_doc_metadata_table):
    ddb_doc_metadata_table.put_item(
        Item={
            "fileName": "test.jpg",
            "tenantId": "test-tenant-id",
            DocumentMetadata.PROCESS_STATUS: ProcessStatus.NOT_STARTED.value,
        }
    )
    return s3_bucket.put_object(
        Key="input/test.jpg",
        Body=JPEG_MAGIC,
        ContentType="image/jpeg",
        Metadata={
            "job-id": "test-job-id",
            "trace-id": "test-trace-id",
            "user-provided-document-category": "income",
            "original-file-name": "original.jpg",
        },
    )


@pytest.fixture
def input_pdf(s3_bucket, ddb_doc_metadata_table):
    ddb_doc_metadata_table.put_item(
        Item={
            "fileName": "test.pdf",
            "tenantId": "test-tenant-id",
            DocumentMetadata.PROCESS_STATUS: ProcessStatus.NOT_STARTED.value,
        }
    )
    return s3_bucket.put_object(
        Key="input/test.pdf",
        Body=PDF_MAGIC,
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
        1,
        False,
    )

    result = invoke_bda(
        input_pdf.bucket_name, input_pdf.key, "test.pdf", "test-tenant-id", "tax_documents"
    )

    assert result["invocationArn"] == "arn:aws:bedrock:us-east-1:123456789012:job/abc123"
    mock_set_status.assert_called_once_with(
        object_key="test.pdf",
        bda_invocation_arn="arn:aws:bedrock:us-east-1:123456789012:job/abc123",
        bda_project_arn_used="arn:aws:bedrock:us-east-1:123456789012:project/test",
        used_category_specific_project=False,
        pages_sent_to_bda=1,
        bda_invoke_duration_seconds=ANY,
        bda_invoke_retry_count=0,
    )
    assert isinstance(mock_set_status.call_args.kwargs["bda_invoke_duration_seconds"], Decimal)
    assert mock_set_status.call_args.kwargs["bda_invoke_duration_seconds"] >= 0


def test_invoke_bda_retryable_failure(input_pdf, mock_invoke_bda, mocker):
    """Transient errors (ThrottlingException) exhaust retries -> RetryError -> classify_as_failed."""
    mock_classify = mocker.patch("documentai_api.jobs.document_processor.main.classify_as_failed")

    mock_low_level_invoke = mocker.patch(
        "documentai_api.jobs.document_processor.main.invoke_bedrock_data_automation"
    )
    mock_low_level_invoke.side_effect = ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
        "invoke_bedrock_data_automation",
    )

    with pytest.raises(RetryError):
        invoke_bda(input_pdf.bucket_name, input_pdf.key, "test.pdf", "test-tenant-id")

    mock_classify.assert_called_once()
    assert mock_classify.call_args.kwargs["object_key"] == "test.pdf"
    assert mock_classify.call_args.kwargs["error_message"] == "BDA invocation failed"


def test_invoke_bda_non_retryable_failure(input_pdf, mock_invoke_bda, mocker):
    """Non-retryable errors (ValidationException) raise ClientError immediately, no retries."""
    mock_low_level_invoke = mocker.patch(
        "documentai_api.jobs.document_processor.main.invoke_bedrock_data_automation"
    )
    mock_low_level_invoke.side_effect = ClientError(
        {"Error": {"Code": "ValidationException", "Message": "Invalid ARN"}},
        "invoke_bedrock_data_automation",
    )

    with pytest.raises(ClientError):
        invoke_bda(input_pdf.bucket_name, input_pdf.key, "test.pdf", "test-tenant-id")

    mock_low_level_invoke.assert_called_once()  # no retries


def test_main_first_time_pdf(input_pdf, mocker, ddb_doc_metadata_table, mock_invoke_bda):
    """Test first time processing PDF (no grayscale needed)."""
    main(input_pdf.key, input_pdf.bucket_name)

    expected_object_key = "test.pdf"

    ddb_record = ddb_doc_metadata_table.get_item(Key={"fileName": expected_object_key})["Item"]
    # The atomic claim transitions the status to STARTED before BDA is invoked.
    assert ddb_record[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.STARTED

    mock_invoke_bda.assert_called_once_with(
        input_pdf.bucket_name,
        input_pdf.key,
        expected_object_key,
        "test-tenant-id",
        PreclassificationCategory.INCOME,
        None,
    )


def test_main_strips_tenant_prefix_for_ddb_key(s3_bucket, ddb_doc_metadata_table, mock_invoke_bda):
    """A tenant-prefixed S3 object resolves to a bare (basename) DDB key.

    The API pre-inserts the job record under the un-prefixed filename, so the
    processor must key off the basename to update it in place. S3 operations,
    by contrast, must keep the full tenant-prefixed key.
    """
    tenant_key = "input/test-tenant-id/test-file-name.pdf"
    obj = s3_bucket.put_object(
        Key=tenant_key,
        Body=PDF_MAGIC,
        ContentType="application/pdf",
        Metadata={
            "job-id": "test-job-id",
            "trace-id": "test-trace-id",
            "user-provided-document-category": "income",
            "original-file-name": "original.pdf",
        },
    )

    # Can't use input_pdf fixture here - we need a tenant-prefixed key to test stripping.
    ddb_doc_metadata_table.put_item(
        Item={
            "fileName": "test-file-name.pdf",
            "tenantId": "test-tenant-id",
            DocumentMetadata.PROCESS_STATUS: ProcessStatus.NOT_STARTED.value,
        }
    )

    main(obj.key, obj.bucket_name)

    # DDB key is the basename, with the tenant segment stripped.
    expected_ddb_key = "test-file-name.pdf"
    record = ddb_doc_metadata_table.get_item(Key={"fileName": expected_ddb_key})["Item"]
    # The atomic claim transitions the status to STARTED before BDA is invoked.
    assert record[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.STARTED

    # S3 operations still receive the full tenant-prefixed key.
    mock_invoke_bda.assert_called_once_with(
        obj.bucket_name,
        tenant_key,
        expected_ddb_key,
        "test-tenant-id",
        PreclassificationCategory.INCOME,
        None,
    )


def test_main_first_time_image(input_image, mocker, ddb_doc_metadata_table, mock_invoke_bda):
    """Test first time processing image (needs grayscale)."""
    mock_optimize = mocker.patch("documentai_api.jobs.document_processor.main.optimize_s3_image")
    mock_optimize.return_value = OptimizationResult(
        crop_result=CropResult(), grayscale_applied=True, file_size_bytes=100, too_large=False
    )

    main(input_image.key, input_image.bucket_name)

    expected_object_key = "test.jpg"

    ddb_record = ddb_doc_metadata_table.get_item(Key={"fileName": expected_object_key})["Item"]
    # The atomic claim transitions the status to STARTED before BDA is invoked.
    assert ddb_record[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.STARTED

    mock_optimize.assert_called_once_with(
        input_image.bucket_name,
        input_image.key,
        apply_grayscale=True,
        file_bytes=ANY,
        content_type="image/jpeg",
        precomputed_bbox=ANY,
    )
    mock_invoke_bda.assert_called_once_with(
        input_image.bucket_name,
        input_image.key,
        expected_object_key,
        "test-tenant-id",
        PreclassificationCategory.INCOME,
        None,
    )


def test_main_grayscale_conversion_fails(input_image, mocker, mock_invoke_bda):
    """Test grayscale conversion failure (too large) marks as not implemented."""
    mocker.patch("documentai_api.jobs.document_processor.main.upsert_initial_ddb_record")
    # DDB is fully mocked here, so stub the atomic claim as successful.
    mocker.patch(
        "documentai_api.jobs.document_processor.main.set_processing_status_started",
        return_value=True,
    )

    mock_optimize = mocker.patch("documentai_api.jobs.document_processor.main.optimize_s3_image")
    mock_optimize.return_value = OptimizationResult(
        crop_result=CropResult(), grayscale_applied=False, file_size_bytes=999999999, too_large=True
    )

    mock_classify = mocker.patch(
        "documentai_api.jobs.document_processor.main.classify_as_not_implemented"
    )

    mock_get = mocker.patch("documentai_api.jobs.document_processor.main.get_ddb_record")
    mock_get.return_value = {
        DocumentMetadata.TENANT_ID: "test-tenant-id",
        DocumentMetadata.PROCESS_STATUS: ProcessStatus.PENDING_IMAGE_OPTIMIZATION.value,
    }

    main(input_image.key, input_image.bucket_name)

    mock_classify.assert_called_once()
    mock_invoke_bda.assert_not_called()


def test_main_rejects_disguised_content(s3_bucket, mocker, mock_invoke_bda):
    """A presigned upload whose bytes aren't BDA-native is failed before BDA.

    S3's POST policy only enforces the declared Content-Type, so a caller can
    store arbitrary bytes under content_type=application/pdf. The processor must
    re-sniff the actual content and reject non-document uploads (SEC-HIGH-05).
    """
    obj = s3_bucket.put_object(
        Key="input/evil.pdf",
        Body=b"MZ\x90\x00\x03\x00\x00\x00",  # PE/exe magic, not a document
        ContentType="application/pdf",
        Metadata={
            "job-id": "test-job-id",
            "trace-id": "test-trace-id",
            "original-file-name": "evil.pdf",
        },
    )
    mocker.patch("documentai_api.jobs.document_processor.main.upsert_initial_ddb_record")
    mock_classify = mocker.patch("documentai_api.jobs.document_processor.main.classify_as_failed")
    mock_get = mocker.patch("documentai_api.jobs.document_processor.main.get_ddb_record")
    mock_get.return_value = {DocumentMetadata.PROCESS_STATUS: ProcessStatus.NOT_STARTED.value}

    main(obj.key, obj.bucket_name)

    mock_invoke_bda.assert_not_called()
    mock_classify.assert_called_once()
    assert mock_classify.call_args.kwargs["object_key"] == "evil.pdf"


def test_main_already_processed(input_pdf, mocker, mock_invoke_bda):
    """Test that already processed files are skipped."""
    mock_get = mocker.patch("documentai_api.jobs.document_processor.main.get_ddb_record")
    mock_get.return_value = {DocumentMetadata.PROCESS_STATUS: ProcessStatus.SUCCESS.value}

    main(input_pdf.key, input_pdf.bucket_name)

    mock_invoke_bda.assert_not_called()


def test_main_missing_tenant_id_calls_classify_as_failed(input_pdf, mocker, mock_invoke_bda):
    """A record with no tenantId is failed; neither Textract nor BDA is invoked."""
    mock_get = mocker.patch("documentai_api.jobs.document_processor.main.get_ddb_record")
    mock_get.return_value = {DocumentMetadata.PROCESS_STATUS: ProcessStatus.NOT_STARTED.value}
    mocker.patch("documentai_api.jobs.document_processor.main.upsert_initial_ddb_record")
    mock_classify = mocker.patch("documentai_api.jobs.document_processor.main.classify_as_failed")
    mock_textract = mocker.patch(f"{_MAIN_MODULE}.run_textract_pipeline")

    main(input_pdf.key, input_pdf.bucket_name)

    mock_classify.assert_called_once()
    assert (
        mock_classify.call_args.kwargs["error_message"]
        == "tenant_id is required for document processing"
    )
    mock_textract.assert_not_called()
    mock_invoke_bda.assert_not_called()


def test_main_uses_env_bucket_when_not_provided(input_pdf, mocker, mock_invoke_bda):
    """Test bucket name defaults to environment variable."""
    main(input_pdf.key)

    mock_invoke_bda.assert_called_once_with(
        input_pdf.bucket_name,
        input_pdf.key,
        "test.pdf",
        "test-tenant-id",
        PreclassificationCategory.INCOME,
        None,
    )


def test_main_idempotent_on_duplicate_events(input_pdf, mocker, mock_invoke_bda):
    """Test job is idempotent when receiving duplicate S3 events."""
    mock_get = mocker.patch("documentai_api.jobs.document_processor.main.get_ddb_record")
    mock_get.return_value = {DocumentMetadata.PROCESS_STATUS: ProcessStatus.STARTED.value}

    main(input_pdf.key, input_pdf.bucket_name)

    mock_invoke_bda.assert_not_called()


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


# =============================================================================
# s3_fetch_duration ordering and arithmetic
# =============================================================================


def test_s3_fetch_duration_measured_after_body_read(mocker):
    """Timer stop must come after Body.read() - guards against the header-only measurement bug."""
    call_order: list[str] = []

    def _monotonic() -> float:
        call_order.append("monotonic")
        return 0.0

    def _read() -> bytes:
        call_order.append("read")
        return b"%PDF-1.4"

    mocker.patch(f"{_MAIN_MODULE}.time.monotonic", side_effect=_monotonic)
    mock_body = Mock()
    mock_body.read.side_effect = _read
    mocker.patch(
        f"{_MAIN_MODULE}.s3_service.get_object",
        return_value={
            "Body": mock_body,
            "ContentType": "application/pdf",
            "ContentLength": 8,
            "Metadata": {
                "job-id": "test-job-id",
                "trace-id": "test-trace-id",
                "original-file-name": "test-file-name.pdf",
                "user-provided-document-category": "income",
            },
        },
    )
    mocker.patch(f"{_MAIN_MODULE}.upsert_initial_ddb_record")
    mocker.patch(
        f"{_MAIN_MODULE}.get_ddb_record",
        side_effect=[
            None,
            {DocumentMetadata.PROCESS_STATUS: ProcessStatus.SUCCESS.value},
        ],
    )

    main("input/f.pdf", "bucket")

    assert call_order == ["monotonic", "read", "monotonic"]


def test_s3_fetch_duration_arithmetic(mocker):
    """Duration is (stop - start) rounded to 3 decimal places as a Decimal."""
    mocker.patch(
        f"{_MAIN_MODULE}.time.monotonic",
        side_effect=[10.0, 15.1234],
    )
    mock_body = Mock()
    mock_body.read.return_value = b"%PDF-1.4"
    mocker.patch(
        f"{_MAIN_MODULE}.s3_service.get_object",
        return_value={
            "Body": mock_body,
            "ContentType": "application/pdf",
            "ContentLength": 8,
            "Metadata": {
                "job-id": "test-job-id",
                "trace-id": "test-trace-id",
                "original-file-name": "test-file-name.pdf",
                "user-provided-document-category": "income",
            },
        },
    )
    mock_upsert = mocker.patch(f"{_MAIN_MODULE}.upsert_initial_ddb_record")
    mocker.patch(
        f"{_MAIN_MODULE}.get_ddb_record",
        side_effect=[
            None,
            {DocumentMetadata.PROCESS_STATUS: ProcessStatus.SUCCESS.value},
        ],
    )

    main("input/f.pdf", "bucket")

    assert mock_upsert.call_args.kwargs["s3_fetch_duration_seconds"] == Decimal("5.123")


# =============================================================================
# _invoke_bda retry count
# =============================================================================


@pytest.mark.parametrize("retry_count", [0, 1, 2])
def test_invoke_bda_retry_count(mocker, retry_count):
    throttle = ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
        "InvokeDataAutomation",
    )
    mock_set_started = mocker.patch(f"{_MAIN_MODULE}.set_bda_processing_status_started")
    mocker.patch(
        f"{_MAIN_MODULE}.invoke_bedrock_data_automation",
        side_effect=[throttle] * retry_count + [("arn", "proj-arn", 1, False)],
    )

    _invoke_bda("bucket", "key", "ddb-key", "test-tenant-id")

    assert mock_set_started.call_args.kwargs["bda_invoke_retry_count"] == retry_count


def test_bda_invoke_duration_arithmetic(mocker):
    """bda_invoke_duration_seconds is a Decimal reflecting the actual invoke wall time."""
    mock_set_started = mocker.patch(f"{_MAIN_MODULE}.set_bda_processing_status_started")

    def slow_invoke(*a, **kw):
        time.sleep(0.05)
        return ("arn", "proj-arn", 1, False)

    mocker.patch(f"{_MAIN_MODULE}.invoke_bedrock_data_automation", side_effect=slow_invoke)

    _invoke_bda("bucket", "key", "ddb-key", "test-tenant-id")

    duration = mock_set_started.call_args.kwargs["bda_invoke_duration_seconds"]
    assert Decimal("0.05") <= duration < Decimal("0.5")


# =============================================================================
# _should_invoke_bda tests
# =============================================================================


def test_should_invoke_bda_with_real_category(mocker):
    """A real category always invokes BDA regardless of flag."""
    mocker.patch(
        "documentai_api.jobs.document_processor.main.skip_bda_if_unclassified",
        return_value=True,
    )
    assert _should_invoke_bda("tax_documents") is True


def test_should_invoke_bda_other_document_flag_off(mocker):
    """'other_document' with skip flag OFF → invoke BDA."""
    mocker.patch(
        "documentai_api.jobs.document_processor.main.skip_bda_if_unclassified",
        return_value=False,
    )
    assert _should_invoke_bda("other_document") is True


def test_should_invoke_bda_other_document_flag_on(mocker):
    """'other_document' with skip flag ON → skip BDA."""
    mocker.patch(
        "documentai_api.jobs.document_processor.main.skip_bda_if_unclassified",
        return_value=True,
    )
    assert _should_invoke_bda("other_document") is False


def test_should_invoke_bda_none_flag_off(mocker):
    """None category with skip flag OFF → invoke BDA."""
    mocker.patch(
        "documentai_api.jobs.document_processor.main.skip_bda_if_unclassified",
        return_value=False,
    )
    assert _should_invoke_bda(None) is True


def test_should_invoke_bda_none_flag_on(mocker):
    """None category with skip flag ON → skip BDA."""
    mocker.patch(
        "documentai_api.jobs.document_processor.main.skip_bda_if_unclassified",
        return_value=True,
    )
    assert _should_invoke_bda(None) is False


# =============================================================================
# BDA skip flow (no blueprint match + flag off)
# =============================================================================


def test_main_skips_bda_when_no_match_and_flag_on(input_pdf, mocker, mock_invoke_bda):
    """When no blueprint matched and skip flag is on, BDA is skipped."""
    mocker.patch(
        "documentai_api.jobs.document_processor.main.skip_bda_if_unclassified",
        return_value=True,
    )
    mocker.patch(
        f"{_LIFECYCLE_MODULE}.preclassify_document",
        return_value=BedrockClassificationResult(
            document_type="other_document",
            confidence=0.5,
            max_document_count_on_page=1,
        ),
    )

    mock_classify_no_match = mocker.patch(
        "documentai_api.jobs.document_processor.main.classify_as_extraction_not_configured"
    )

    mock_get = mocker.patch("documentai_api.jobs.document_processor.main.get_ddb_record")
    mock_get.return_value = {
        DocumentMetadata.TENANT_ID: "test-tenant-id",
        DocumentMetadata.PROCESS_STATUS: ProcessStatus.NOT_STARTED.value,
        DocumentMetadata.PRECLASSIFICATION_CATEGORY: "other_document",
    }
    mocker.patch("documentai_api.jobs.document_processor.main.upsert_initial_ddb_record")
    mocker.patch(
        "documentai_api.jobs.document_processor.main.set_processing_status_started",
        return_value=True,
    )
    mocker.patch(
        "documentai_api.jobs.document_processor.main.optimize_s3_image",
        return_value=OptimizationResult(
            crop_result=CropResult(), grayscale_applied=False, file_size_bytes=100, too_large=False
        ),
    )

    main(input_pdf.key, input_pdf.bucket_name)

    mock_invoke_bda.assert_not_called()
    mock_classify_no_match.assert_called_once()


def test_main_invokes_bda_when_match_found(input_pdf, mocker, mock_invoke_bda):
    """When a blueprint matched, BDA is invoked with the routing category."""
    mocker.patch(
        "documentai_api.jobs.document_processor.main.skip_bda_if_unclassified",
        return_value=True,
    )

    mock_get = mocker.patch("documentai_api.jobs.document_processor.main.get_ddb_record")
    mock_get.return_value = {
        DocumentMetadata.TENANT_ID: "test-tenant-id",
        DocumentMetadata.PROCESS_STATUS: ProcessStatus.NOT_STARTED.value,
        DocumentMetadata.PRECLASSIFICATION_CATEGORY: "w2-form",
        DocumentMetadata.PRECLASSIFICATION_BLUEPRINT_MATCH_CATEGORY: PreclassificationCategory.INCOME,
    }
    mocker.patch("documentai_api.jobs.document_processor.main.upsert_initial_ddb_record")
    mocker.patch(
        "documentai_api.jobs.document_processor.main.set_processing_status_started",
        return_value=True,
    )
    mocker.patch(
        "documentai_api.jobs.document_processor.main.optimize_s3_image",
        return_value=OptimizationResult(
            crop_result=CropResult(), grayscale_applied=False, file_size_bytes=100, too_large=False
        ),
    )

    main(input_pdf.key, input_pdf.bucket_name)

    mock_invoke_bda.assert_called_once_with(
        input_pdf.bucket_name,
        input_pdf.key,
        "test.pdf",
        "test-tenant-id",
        PreclassificationCategory.INCOME,
        None,
    )


def test_persist_optimization_metrics_writes_timing_fields(ddb_doc_metadata_table, mocker):
    """opt_result timing fields are written to DDB when provided."""
    ddb_key = "timing-test.png"
    ddb_doc_metadata_table.put_item(Item={"fileName": ddb_key})

    opt = OptimizationResult(
        crop_result=CropResult(),
        crop_block_duration_seconds=Decimal("0.456"),
        write_duration_seconds=Decimal("0.078"),
    )
    _persist_optimization_metrics(ddb_key, opt.crop_result, False, None, opt_result=opt)

    item = ddb_doc_metadata_table.get_item(Key={"fileName": ddb_key})["Item"]
    assert item[DocumentMetadata.IMAGE_OPT_CROP_BLOCK_DURATION_SECONDS] == Decimal("0.456")
    assert item[DocumentMetadata.IMAGE_OPT_WRITE_DURATION_SECONDS] == Decimal("0.078")


def test_persist_optimization_metrics_no_timing_when_opt_result_none(ddb_doc_metadata_table):
    """Without opt_result, no timing fields are written."""
    ddb_key = "no-timing-test.png"
    ddb_doc_metadata_table.put_item(Item={"fileName": ddb_key})

    _persist_optimization_metrics(ddb_key, CropResult(), False, None, opt_result=None)

    item = ddb_doc_metadata_table.get_item(Key={"fileName": ddb_key})["Item"]
    assert DocumentMetadata.IMAGE_OPT_CROP_BLOCK_DURATION_SECONDS not in item
    assert DocumentMetadata.IMAGE_OPT_WRITE_DURATION_SECONDS not in item


# =============================================================================
# Textract identity dispatch
# =============================================================================


@pytest.fixture
def input_identity_image(s3_bucket, ddb_doc_metadata_table):
    ddb_doc_metadata_table.put_item(
        Item={
            "fileName": "id.jpg",
            "tenantId": "test-tenant-id",
            DocumentMetadata.PROCESS_STATUS: ProcessStatus.NOT_STARTED.value,
        }
    )
    return s3_bucket.put_object(
        Key="input/id.jpg",
        Body=JPEG_MAGIC,
        ContentType="image/jpeg",
        Metadata={
            "job-id": "test-job-id",
            "trace-id": "test-trace-id",
            "user-provided-document-category": "identity",
            "original-file-name": "id.jpg",
        },
    )


@pytest.fixture
def mock_preclassify_identity(mocker):
    return mocker.patch(
        f"{_LIFECYCLE_MODULE}.preclassify_document",
        return_value=BedrockClassificationResult(
            document_type="driver's license",
            confidence=0.95,
            max_document_count_on_page=1,
            is_identity_document=True,
        ),
    )


@pytest.fixture
def mock_optimize_s3_image_identity(mocker):
    return mocker.patch(
        "documentai_api.jobs.document_processor.main.optimize_s3_image",
        return_value=OptimizationResult(
            crop_result=CropResult(), grayscale_applied=True, file_size_bytes=100, too_large=False
        ),
    )


def test_main_invokes_textract_for_identity_document(
    input_identity_image, ddb_doc_metadata_table, mocker, mock_invoke_bda, mock_preclassify_identity
):
    """When preclassification flags an identity document, main dispatches to Textract and skips BDA."""
    mock_pipeline = mocker.patch(f"{_MAIN_MODULE}.run_textract_pipeline", return_value=True)

    main(input_identity_image.key, input_identity_image.bucket_name)

    mock_pipeline.assert_called_once()
    mock_invoke_bda.assert_not_called()


def test_main_textract_exception_does_not_abort_pipeline(
    input_identity_image,
    ddb_doc_metadata_table,
    mocker,
    mock_invoke_bda,
    mock_preclassify_identity,
    mock_optimize_s3_image_identity,
):
    """A Textract failure is swallowed; the document still proceeds to BDA."""
    mocker.patch(
        f"{_MAIN_MODULE}.run_textract_pipeline",
        side_effect=RuntimeError("Textract down"),
    )

    main(input_identity_image.key, input_identity_image.bucket_name)  # must not raise
    mock_invoke_bda.assert_called_once()


def test_main_blur_rejected_identity_document_skips_textract(
    input_identity_image, ddb_doc_metadata_table, mocker, mock_invoke_bda, mock_preclassify_identity
):
    """Blur rejection takes precedence over identity routing.

    is_identity_document is only set when blur_outcome.process_status is None; a
    blur-rejected doc never reaches Textract.
    """
    mocker.patch(
        f"{_LIFECYCLE_MODULE}.is_blur_detection_enabled",
        return_value=True,
    )
    mocker.patch(
        f"{_LIFECYCLE_MODULE}.is_blur_rejection_enforced",
        return_value=True,
    )
    mocker.patch(
        f"{_LIFECYCLE_MODULE}.detect_blur",
        return_value=BlurResult(is_blurry=True),
    )
    mock_pipeline = mocker.patch(f"{_MAIN_MODULE}.run_textract_pipeline")

    main(input_identity_image.key, input_identity_image.bucket_name)
    mock_pipeline.assert_not_called()
    mock_invoke_bda.assert_not_called()


def test_main_textract_returns_none_falls_through_to_bda(
    input_identity_image,
    ddb_doc_metadata_table,
    mocker,
    mock_invoke_bda,
    mock_preclassify_identity,
    mock_optimize_s3_image_identity,
):
    """When run_textract_pipeline returns False, the document falls through to BDA."""
    mocker.patch(f"{_MAIN_MODULE}.run_textract_pipeline", return_value=False)
    main(input_identity_image.key, input_identity_image.bucket_name)
    mock_invoke_bda.assert_called_once()


def test_main_textract_extraction_result_none_falls_through_to_bda(
    input_identity_image,
    ddb_doc_metadata_table,
    mocker,
    mock_invoke_bda,
    mock_preclassify_identity,
    mock_optimize_s3_image_identity,
):
    """When run_textract_pipeline returns False, the document falls through to BDA."""
    mocker.patch(f"{_MAIN_MODULE}.run_textract_pipeline", return_value=False)
    main(input_identity_image.key, input_identity_image.bucket_name)
    mock_invoke_bda.assert_called_once()
