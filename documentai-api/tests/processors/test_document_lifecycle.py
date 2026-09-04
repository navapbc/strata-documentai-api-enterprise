from decimal import Decimal
from typing import Any

import pytest
from botocore.exceptions import ClientError

from documentai_api.config.constants import ProcessStatus
from documentai_api.dtos.classification import (
    BedrockClassificationResult,
    ClassificationData,
    PreclassificationMatchResult,
)
from documentai_api.dtos.ddb import UpdateDdbRecord
from documentai_api.dtos.processing import InternalApiResponse
from documentai_api.processors import document_lifecycle as lifecycle_util
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils import document_classification as classification_util
from documentai_api.utils.blur_detection import BlurResult
from documentai_api.utils.response_codes import ResponseCodes

_LIFECYCLE_MODULE = "documentai_api.processors.document_lifecycle"
_CLASSIFICATION_MODULE = "documentai_api.utils.document_classification"


class _Mock:
    GET_PAGE_COUNT = "get_page_count"
    IS_PASSWORD_PROTECTED = "is_password_protected"
    IS_BLUR_DETECTION_ENABLED = "is_blur_detection_enabled"
    IS_BLUR_REJECTION_ENFORCED = "is_blur_rejection_enforced"
    DETECT_BLUR = "detect_blur"
    PRECLASSIFY_DOCUMENT = "preclassify_document"
    FIND_MATCHING_BLUEPRINT = "find_matching_blueprint"
    TRY_TEXTRACT_IDENTITY = "extract_textract_identity"
    FINALIZE_TEXTRACT_RESULT = "process_textract_result"
    IS_MULTIPAGE_DOCUMENT_FLAGGING_ENABLED = "is_multipage_document_flagging_enabled"
    BUILD_V1_API_RESPONSE = "build_v1_api_response"
    GET_BBOX_IF_ENABLED = "get_bbox_if_enabled"


_DEFAULT_PRECLASSIFY = BedrockClassificationResult(
    document_type="W2", confidence=0.95, max_document_count_on_page=1
)
_DEFAULT_BLUR = BlurResult(
    is_blurry=False, is_not_document=False, word_count=20, avg_confidence=95.0
)
_DEFAULT_TEXTRACT_RESULT = {
    "matched_document_class": "US-drivers-licenses",
    "field_confidence_scores": [{"NAME_DETAILS.FIRST_NAME": 0.99}],
    "textract_s3_uri": "s3://test-bucket/output/textract/test-file.json",
    "extract_started_at": "2025-01-01T00:00:00+00:00",
    "extract_completed_at": "2025-01-01T00:00:02+00:00",
    "extract_time": "2.00",
}


@pytest.fixture
def lifecycle_mocks(mocker):
    """Patch all external dependencies of upsert_initial_ddb_record with safe defaults.

    Individual tests override only the specific mock they care about, keeping
    each test focused on a single behaviour rather than repeating boilerplate.
    """
    return {
        _Mock.GET_PAGE_COUNT: mocker.patch(
            f"{_LIFECYCLE_MODULE}.document_utils.get_page_count", return_value=1
        ),
        _Mock.IS_PASSWORD_PROTECTED: mocker.patch(
            f"{_LIFECYCLE_MODULE}.document_utils.is_password_protected", return_value=False
        ),
        _Mock.IS_BLUR_DETECTION_ENABLED: mocker.patch(
            f"{_LIFECYCLE_MODULE}.is_blur_detection_enabled", return_value=True
        ),
        _Mock.IS_BLUR_REJECTION_ENFORCED: mocker.patch(
            f"{_LIFECYCLE_MODULE}.is_blur_rejection_enforced", return_value=True
        ),
        _Mock.DETECT_BLUR: mocker.patch(
            f"{_LIFECYCLE_MODULE}.detect_blur", return_value=_DEFAULT_BLUR
        ),
        _Mock.PRECLASSIFY_DOCUMENT: mocker.patch(
            f"{_LIFECYCLE_MODULE}.preclassify_document", return_value=_DEFAULT_PRECLASSIFY
        ),
        _Mock.FIND_MATCHING_BLUEPRINT: mocker.patch(
            f"{_LIFECYCLE_MODULE}.find_matching_blueprint",
            return_value=PreclassificationMatchResult(),
        ),
        _Mock.TRY_TEXTRACT_IDENTITY: mocker.patch(
            f"{_LIFECYCLE_MODULE}.extract_textract_identity", return_value=None
        ),
        _Mock.FINALIZE_TEXTRACT_RESULT: mocker.patch(
            f"{_LIFECYCLE_MODULE}.process_textract_result"
        ),
        _Mock.IS_MULTIPAGE_DOCUMENT_FLAGGING_ENABLED: mocker.patch(
            f"{_LIFECYCLE_MODULE}.is_multipage_document_flagging_enabled", return_value=True
        ),
        _Mock.BUILD_V1_API_RESPONSE: mocker.patch(
            "documentai_api.utils.ddb.build_v1_api_response", return_value={"status": "completed"}
        ),
        _Mock.GET_BBOX_IF_ENABLED: mocker.patch(
            f"{_LIFECYCLE_MODULE}.get_bbox_if_enabled", return_value=None
        ),
    }


def _upsert(
    s3_bucket: Any,
    content_type: str = "application/pdf",
    ddb_key: str = "test-file",
    user_provided_document_category: str | None = "income",
    **kwargs: Any,
) -> None:
    """Helper to put an S3 object and call upsert_initial_ddb_record."""
    s3_bucket.put_object(Key="input/test-file", Body=b"bytes", ContentType=content_type)
    lifecycle_util.upsert_initial_ddb_record(
        source_bucket_name=s3_bucket.name,
        source_object_key="input/test-file",
        original_file_name="test.pdf",
        ddb_key=ddb_key,
        user_provided_document_category=user_provided_document_category,
        job_id="test-job-id",
        trace_id="test-trace-id",
        **kwargs,
    )


# =============================================================================
# upsert_initial_ddb_record - status routing
# =============================================================================


@pytest.mark.parametrize(
    (
        "user_provided_document_category",
        "content_type",
        "is_password_protected",
        "preclassify_result",
        "expected_status",
        "has_internal_response",
        "blur_result",
    ),
    [
        ("income", "application/pdf", True, None, ProcessStatus.PASSWORD_PROTECTED, True, None),
        (
            "income",
            "application/pdf",
            False,
            BedrockClassificationResult(
                document_type="other_document", confidence=0.3, max_document_count_on_page=1
            ),
            ProcessStatus.BLURRY_DOCUMENT_DETECTED,
            True,
            BlurResult(is_blurry=True, is_not_document=False, avg_confidence=45.0, word_count=3),
        ),
        (
            "income",
            "application/pdf",
            False,
            BedrockClassificationResult(
                document_type="not_a_document", confidence=0.9, max_document_count_on_page=1
            ),
            ProcessStatus.NO_DOCUMENT_DETECTED,
            True,
            BlurResult(is_blurry=False, is_not_document=True, word_count=0),
        ),
        (
            "income",
            "application/pdf",
            False,
            BedrockClassificationResult(
                document_type="W2", confidence=0.95, max_document_count_on_page=2
            ),
            ProcessStatus.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
            True,
            None,
        ),
        (
            "income",
            "image/jpeg",
            False,
            BedrockClassificationResult(
                document_type="W2", confidence=0.95, max_document_count_on_page=1
            ),
            ProcessStatus.PENDING_IMAGE_OPTIMIZATION,
            False,
            None,
        ),
        (
            "income",
            "application/pdf",
            False,
            BedrockClassificationResult(
                document_type="W2", confidence=0.95, max_document_count_on_page=1
            ),
            ProcessStatus.NOT_STARTED,
            False,
            None,
        ),
        (
            None,
            "application/pdf",
            False,
            BedrockClassificationResult(
                document_type="W2", confidence=0.95, max_document_count_on_page=1
            ),
            ProcessStatus.NOT_STARTED,
            False,
            None,
        ),
    ],
)
def test_upsert_initial_ddb_record(
    ddb_doc_metadata_table,
    s3_bucket,
    lifecycle_mocks,
    user_provided_document_category,
    content_type,
    is_password_protected,
    preclassify_result,
    expected_status,
    has_internal_response,
    blur_result,
):
    lifecycle_mocks[_Mock.IS_PASSWORD_PROTECTED].return_value = is_password_protected
    lifecycle_mocks[_Mock.DETECT_BLUR].return_value = blur_result or _DEFAULT_BLUR
    if preclassify_result:
        lifecycle_mocks[_Mock.PRECLASSIFY_DOCUMENT].return_value = preclassify_result

    _upsert(
        s3_bucket,
        content_type=content_type,
        user_provided_document_category=user_provided_document_category,
    )

    item = ddb_doc_metadata_table.get_item(Key={"fileName": "test-file"})["Item"]
    assert item[DocumentMetadata.PROCESS_STATUS] == expected_status
    assert item[DocumentMetadata.CONTENT_TYPE] == content_type
    assert item[DocumentMetadata.PAGES_DETECTED] == 1
    assert item[DocumentMetadata.IS_PASSWORD_PROTECTED] == is_password_protected
    assert item[DocumentMetadata.JOB_ID] == "test-job-id"
    assert item[DocumentMetadata.TRACE_ID] == "test-trace-id"
    assert DocumentMetadata.CREATED_AT in item
    assert DocumentMetadata.UPDATED_AT in item

    if preclassify_result and not (
        blur_result and (blur_result.is_blurry or blur_result.is_not_document)
    ):
        assert item[DocumentMetadata.PRECLASSIFICATION_CATEGORY] == preclassify_result.document_type

    if has_internal_response:
        assert DocumentMetadata.RESPONSE_JSON in item
        assert DocumentMetadata.V1_API_RESPONSE_JSON in item
    else:
        assert DocumentMetadata.RESPONSE_JSON not in item


@pytest.mark.parametrize(
    ("blur_result", "expected_status"),
    [
        (
            BlurResult(is_blurry=True, is_not_document=False, word_count=3, avg_confidence=45.0),
            ProcessStatus.BLURRY_DOCUMENT_DETECTED,
        ),
        (
            BlurResult(is_blurry=False, is_not_document=True, word_count=0),
            ProcessStatus.NO_DOCUMENT_DETECTED,
        ),
    ],
)
def test_blur_rejection_runs_preclassification_concurrently(
    ddb_doc_metadata_table, s3_bucket, lifecycle_mocks, blur_result, expected_status
):
    """Blur and preclassification concurrent execution validation."""
    lifecycle_mocks[_Mock.DETECT_BLUR].return_value = blur_result

    _upsert(s3_bucket)

    lifecycle_mocks[_Mock.PRECLASSIFY_DOCUMENT].assert_called_once()
    item = ddb_doc_metadata_table.get_item(Key={"fileName": "test-file"})["Item"]
    assert item[DocumentMetadata.PROCESS_STATUS] == expected_status


@pytest.mark.parametrize(
    "content_type", ["image/jpeg", "image/png", "image/tiff", "application/pdf"]
)
def test_bbox_detection_submitted_concurrently(
    ddb_doc_metadata_table, s3_bucket, lifecycle_mocks, content_type
):
    """get_bbox_if_enabled is always submitted concurrently regardless of content type."""
    _upsert(s3_bucket, content_type=content_type)

    lifecycle_mocks[_Mock.GET_BBOX_IF_ENABLED].assert_called_once()


@pytest.mark.parametrize(
    "content_type", ["image/jpeg", "image/png", "image/tiff", "application/pdf"]
)
def test_upsert_returns_bbox_future_for_all_image_and_pdf_types(
    ddb_doc_metadata_table, s3_bucket, lifecycle_mocks, content_type
):
    """upsert_initial_ddb_record returns a non-None future for all types that proceed to extraction."""
    s3_bucket.put_object(Key="input/test-file", Body=b"bytes", ContentType=content_type)
    result = lifecycle_util.upsert_initial_ddb_record(
        source_bucket_name=s3_bucket.name,
        source_object_key="input/test-file",
        original_file_name="test.pdf",
        ddb_key="test-file",
        user_provided_document_category="income",
        job_id="test-job-id",
        trace_id="test-trace-id",
    )

    assert result is not None


def test_blur_detection_without_enforcement_proceeds_to_preclassify(
    ddb_doc_metadata_table, s3_bucket, lifecycle_mocks
):
    """When blur is detected but enforcement is off, preclassification still runs."""
    lifecycle_mocks[_Mock.IS_BLUR_REJECTION_ENFORCED].return_value = False
    lifecycle_mocks[_Mock.DETECT_BLUR].return_value = BlurResult(
        is_blurry=True, word_count=10, avg_confidence=50.0
    )

    _upsert(s3_bucket, content_type="image/jpeg")

    lifecycle_mocks[_Mock.PRECLASSIFY_DOCUMENT].assert_called_once()
    item = ddb_doc_metadata_table.get_item(Key={"fileName": "test-file"})["Item"]
    assert item[DocumentMetadata.IS_DOCUMENT_BLURRY] is True
    assert item[DocumentMetadata.PRECLASSIFICATION_CATEGORY] == "W2"


def test_blur_analysis_failure_logs_and_continues_to_preclassify(
    ddb_doc_metadata_table, s3_bucket, lifecycle_mocks
):
    """When blur analysis fails, a warning is logged and preclassification still runs."""
    lifecycle_mocks[_Mock.DETECT_BLUR].return_value = BlurResult(
        is_blurry=False, is_not_document=False, word_count=0, analysis_failed=True
    )

    _upsert(s3_bucket)

    lifecycle_mocks[_Mock.PRECLASSIFY_DOCUMENT].assert_called_once()
    item = ddb_doc_metadata_table.get_item(Key={"fileName": "test-file"})["Item"]
    assert item[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.NOT_STARTED


def test_upsert_initial_ddb_record_sampling_excluded(
    ddb_doc_metadata_table, s3_bucket, lifecycle_mocks, mocker
):
    """Document excluded by sampling skips blur/preclassification and is marked excluded."""
    mocker.patch(f"{_LIFECYCLE_MODULE}.is_selected_for_processing", return_value=(False, 0.5, 0.6))
    mock_decrement = mocker.patch("documentai_api.utils.write_limit.decrement")
    mock_put_metric = mocker.patch(f"{_LIFECYCLE_MODULE}.cloudwatch_service.put_metric_data")

    _upsert(s3_bucket, tenant_id="tenant-1", upload_date="2026-07-31")

    lifecycle_mocks[_Mock.PRECLASSIFY_DOCUMENT].assert_not_called()
    mock_decrement.assert_called_once_with("tenant-1", "2026-07-31")
    mock_put_metric.assert_called_once_with(
        "DocumentAI/DocumentProcessor",
        "ProcessingExcludedBySampling",
        1,
        dimensions={"Category": "income"},
    )
    item = ddb_doc_metadata_table.get_item(Key={"fileName": "test-file"})["Item"]
    assert item[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.PROCESSING_EXCLUDED
    assert DocumentMetadata.RESPONSE_JSON in item


def test_upsert_initial_ddb_record_sampling_not_applied_to_password_protected(
    ddb_doc_metadata_table, s3_bucket, lifecycle_mocks, mocker
):
    """Password-protected documents skip sampling - they're already terminal."""
    lifecycle_mocks[_Mock.IS_PASSWORD_PROTECTED].return_value = True
    mock_sampling = mocker.patch(f"{_LIFECYCLE_MODULE}.is_selected_for_processing")

    _upsert(s3_bucket, tenant_id="tenant-1")

    mock_sampling.assert_not_called()
    item = ddb_doc_metadata_table.get_item(Key={"fileName": "test-file"})["Item"]
    assert item[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.PASSWORD_PROTECTED


# =============================================================================
# BDA / atomic status setters
# =============================================================================


def test_set_bda_processing_status_started_routed_to_category(mocker):
    """used_category_specific_project is passed straight through to the DDB update."""
    mock_update = mocker.patch(f"{_LIFECYCLE_MODULE}.update_ddb")

    lifecycle_util.set_bda_processing_status_started(
        "test-file",
        "arn:aws:bda:us-east-1:123:job/1",
        "arn:aws:project/123",
        used_category_specific_project=True,
    )
    mock_update.assert_called_once_with(
        UpdateDdbRecord(
            object_key="test-file",
            status=ProcessStatus.STARTED,
            internal_api_response=None,
            bda_invocation_arn="arn:aws:bda:us-east-1:123:job/1",
            bda_project_arn_used="arn:aws:project/123",
            used_category_specific_project=True,
            pages_sent_to_bda=None,
            bda_invoke_duration_seconds=None,
            bda_invoke_retry_count=None,
        )
    )


def test_set_bda_processing_status_started_falls_back_to_all(mocker):
    """used_category_specific_project defaults to False when the caller doesn't pass it."""
    mock_update = mocker.patch(f"{_LIFECYCLE_MODULE}.update_ddb")

    lifecycle_util.set_bda_processing_status_started(
        "test-file", "arn:aws:bda:us-east-1:123:job/1", "arn:aws:project/all"
    )
    mock_update.assert_called_once_with(
        UpdateDdbRecord(
            object_key="test-file",
            status=ProcessStatus.STARTED,
            internal_api_response=None,
            bda_invocation_arn="arn:aws:bda:us-east-1:123:job/1",
            bda_project_arn_used="arn:aws:project/all",
            used_category_specific_project=False,
            pages_sent_to_bda=None,
            bda_invoke_duration_seconds=None,
            bda_invoke_retry_count=None,
        )
    )


def test_set_bda_processing_status_not_started(mocker):
    mock_update = mocker.patch(f"{_LIFECYCLE_MODULE}.update_ddb")
    lifecycle_util.set_bda_processing_status_not_started("test-file")
    mock_update.assert_called_once_with(
        UpdateDdbRecord(
            object_key="test-file",
            status=ProcessStatus.NOT_STARTED,
            internal_api_response=None,
        )
    )


def test_set_processing_status_started_claims_when_status_matches(ddb_doc_metadata_table):
    """Atomic claim succeeds and flips status to STARTED when the expected status matches."""
    ddb_doc_metadata_table.put_item(
        Item={
            "fileName": "claim-test",
            DocumentMetadata.PROCESS_STATUS: ProcessStatus.PENDING_IMAGE_OPTIMIZATION.value,
        }
    )
    claimed = lifecycle_util.set_processing_status_started(
        "claim-test", ProcessStatus.PENDING_IMAGE_OPTIMIZATION.value
    )
    assert claimed is True
    item = ddb_doc_metadata_table.get_item(Key={"fileName": "claim-test"})["Item"]
    assert item[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.STARTED


def test_set_processing_status_started_returns_false_when_already_claimed(ddb_doc_metadata_table):
    """A duplicate invocation loses the race: the conditional update fails, status untouched."""
    ddb_doc_metadata_table.put_item(
        Item={
            "fileName": "claim-test",
            DocumentMetadata.PROCESS_STATUS: ProcessStatus.STARTED.value,
        }
    )
    claimed = lifecycle_util.set_processing_status_started(
        "claim-test", ProcessStatus.PENDING_IMAGE_OPTIMIZATION.value
    )
    assert claimed is False
    item = ddb_doc_metadata_table.get_item(Key={"fileName": "claim-test"})["Item"]
    assert item[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.STARTED


def test_set_processing_status_started_returns_false_when_record_missing(ddb_doc_metadata_table):
    """No record to claim (never upserted) -> conditional update fails, returns False."""
    assert (
        lifecycle_util.set_processing_status_started(
            "does-not-exist", ProcessStatus.PENDING_IMAGE_OPTIMIZATION.value
        )
        is False
    )


def test_set_processing_status_started_reraises_non_conditional_client_errors(
    ddb_doc_metadata_table, mocker
):
    """Non-ConditionalCheckFailedException ClientErrors are re-raised, not swallowed."""
    error = ClientError(
        {"Error": {"Code": "ProvisionedThroughputExceededException", "Message": "throttled"}},
        "UpdateItem",
    )
    mocker.patch("documentai_api.services.ddb.update_item", side_effect=error)
    with pytest.raises(ClientError, match="ProvisionedThroughputExceededException"):
        lifecycle_util.set_processing_status_started(
            "some-key", ProcessStatus.PENDING_IMAGE_OPTIMIZATION.value
        )


# =============================================================================
# classify_as_* functions
# =============================================================================


@pytest.mark.parametrize(
    ("function", "response_code", "status", "matched_document_class", "error_msg"),
    [
        (
            classification_util.classify_as_success,
            ResponseCodes.SUCCESS,
            ProcessStatus.SUCCESS,
            "paystub",
            None,
        ),
        (
            classification_util.classify_as_failed,
            ResponseCodes.INTERNAL_PROCESSING_ERROR,
            ProcessStatus.FAILED,
            None,
            "Test error",
        ),
        (
            classification_util.classify_as_not_implemented,
            ResponseCodes.NO_BLUEPRINT_MATCHED,
            ProcessStatus.SUCCESS,
            None,
            None,
        ),
        (
            classification_util.classify_as_no_document_detected,
            ResponseCodes.NO_DOCUMENT_DETECTED,
            ProcessStatus.NO_DOCUMENT_DETECTED,
            None,
            None,
        ),
        (
            classification_util.classify_as_no_custom_blueprint_matched,
            ResponseCodes.NO_BLUEPRINT_MATCHED,
            ProcessStatus.NO_CUSTOM_BLUEPRINT_MATCHED,
            None,
            None,
        ),
    ],
)
def test_classify_functions(
    function, response_code, status, matched_document_class, error_msg, mocker
):

    data = ClassificationData(matched_document_class="paystub")
    fake_response = InternalApiResponse(
        validation_passed=True,
        document_category=None,
        matched_document_class=None,
        response_code="000",
        response_message="ok",
    )
    mock_get_response = mocker.patch(
        f"{_CLASSIFICATION_MODULE}.get_internal_api_response", return_value=fake_response
    )
    mock_update = mocker.patch(f"{_CLASSIFICATION_MODULE}.update_ddb")

    args = ["test-file", data]
    if error_msg:
        args.insert(1, error_msg)
    elif response_code == ResponseCodes.SUCCESS:
        args.insert(1, response_code)

    function(*args)

    mock_get_response.assert_called_once_with(
        object_key="test-file",
        response_code=response_code,
        matched_document_class=matched_document_class,
    )

    expected_dto = UpdateDdbRecord(
        object_key="test-file",
        status=status,
        internal_api_response=fake_response,
        data=data,
    )
    if error_msg:
        expected_dto = expected_dto.model_copy(update={"error_message": error_msg})
    if function == classification_util.classify_as_success:
        expected_dto = expected_dto.model_copy(
            update=dict(
                below_extraction_confidence_floor=False,
                extraction_rules_configured=None,
                missing_required_field_list=None,
                required_field_list=None,
                applied_extraction_confidence_floor=None,
                used_default_confidence_floor=None,
                result_processor_started_at=None,
            )
        )
    if function in (
        classification_util.classify_as_failed,
        classification_util.classify_as_no_document_detected,
        classification_util.classify_as_no_custom_blueprint_matched,
    ):
        expected_dto = expected_dto.model_copy(update={"result_processor_started_at": None})

    assert mock_update.call_args.args[0] == expected_dto


def test_classify_as_ai_consent_declined(mocker):

    fake_response = InternalApiResponse(
        validation_passed=True,
        document_category=None,
        matched_document_class=None,
        response_code="000",
        response_message="ok",
    )
    mock_get_response = mocker.patch(
        f"{_CLASSIFICATION_MODULE}.get_internal_api_response", return_value=fake_response
    )
    mock_update = mocker.patch(f"{_CLASSIFICATION_MODULE}.update_ddb")

    classification_util.classify_as_ai_consent_declined("test-file")

    mock_get_response.assert_called_once_with(
        object_key="test-file",
        response_code=ResponseCodes.AI_CONSENT_DECLINED,
        matched_document_class=None,
    )
    assert mock_update.call_args.args[0] == UpdateDdbRecord(
        object_key="test-file",
        status=ProcessStatus.AI_CONSENT_DECLINED,
        internal_api_response=fake_response,
    )


# =============================================================================
# is_selected_for_processing
# =============================================================================


@pytest.mark.parametrize(
    ("tenant_id", "category_name", "bda_percentage", "random_val", "expected"),
    [
        (None, "income", None, None, (True, None, None)),
        ("t1", None, None, None, (True, None, None)),
        ("t1", "income", 1.0, None, (True, 1.0, None)),
        ("t1", "income", 0.5, 0.4, (True, 0.5, 0.4)),
        ("t1", "income", 0.5, 0.6, (False, 0.5, 0.6)),
        ("t1", "income", 0.0, 0.0, (False, 0.0, 0.0)),
    ],
)
def test_is_selected_for_processing(
    tenant_id, category_name, bda_percentage, random_val, expected, mocker
):
    if bda_percentage is not None:
        mocker.patch(
            "documentai_api.utils.document_categories.get_processing_percentage",
            return_value=bda_percentage,
        )
    if random_val is not None:
        mocker.patch(f"{_LIFECYCLE_MODULE}.random.random", return_value=random_val)
    assert lifecycle_util.is_selected_for_processing(tenant_id, category_name) == expected


# =============================================================================
# Textract identity routing
# =============================================================================


def test_upsert_initial_ddb_record_routes_to_textract_when_enabled(
    ddb_doc_metadata_table, s3_bucket, lifecycle_mocks
):
    """When textract flag is on and user category is identity, routes to Textract."""
    lifecycle_mocks[_Mock.PRECLASSIFY_DOCUMENT].return_value = BedrockClassificationResult(
        document_type="driver's license",
        confidence=0.95,
        max_document_count_on_page=1,
        is_identity_document=True,
    )
    lifecycle_mocks[_Mock.TRY_TEXTRACT_IDENTITY].return_value = _DEFAULT_TEXTRACT_RESULT

    _upsert(s3_bucket, content_type="image/jpeg", user_provided_document_category="identity")

    lifecycle_mocks[_Mock.TRY_TEXTRACT_IDENTITY].assert_called_once()
    lifecycle_mocks[_Mock.FINALIZE_TEXTRACT_RESULT].assert_called_once_with(
        "test-file", _DEFAULT_TEXTRACT_RESULT, "identity", None
    )
    item = ddb_doc_metadata_table.get_item(Key={"fileName": "test-file"})["Item"]
    assert item[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.STARTED


def test_upsert_initial_ddb_record_unknown_category_with_textract_does_not_crash(
    ddb_doc_metadata_table, s3_bucket, lifecycle_mocks
):
    """Regression: user_provided_document_category=None must not crash with Textract path."""
    lifecycle_mocks[_Mock.PRECLASSIFY_DOCUMENT].return_value = BedrockClassificationResult(
        document_type="driver's license", confidence=0.95, max_document_count_on_page=1
    )

    _upsert(s3_bucket, content_type="image/jpeg", user_provided_document_category=None)

    lifecycle_mocks[_Mock.TRY_TEXTRACT_IDENTITY].assert_not_called()
    item = ddb_doc_metadata_table.get_item(Key={"fileName": "test-file"})["Item"]
    assert item[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.PENDING_IMAGE_OPTIMIZATION


def test_upsert_initial_ddb_record_falls_through_when_textract_returns_none(
    ddb_doc_metadata_table, s3_bucket, lifecycle_mocks
):
    """When textract returns None (flag off or failure), falls through to BDA path."""
    lifecycle_mocks[_Mock.PRECLASSIFY_DOCUMENT].return_value = BedrockClassificationResult(
        document_type="driver's license", confidence=0.95, max_document_count_on_page=1
    )

    _upsert(s3_bucket, content_type="image/jpeg", user_provided_document_category="identity")

    item = ddb_doc_metadata_table.get_item(Key={"fileName": "test-file"})["Item"]
    assert item[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.PENDING_IMAGE_OPTIMIZATION


# =============================================================================
# Blueprint matching
# =============================================================================


def test_upsert_initial_ddb_record_stores_blueprint_match_fields(
    ddb_doc_metadata_table, s3_bucket, lifecycle_mocks
):
    """Blueprint match result fields are persisted to DDB."""
    lifecycle_mocks[_Mock.FIND_MATCHING_BLUEPRINT].return_value = PreclassificationMatchResult(
        matched_document_type="W2",
        confidence=0.92,
        category="income",
        input_tokens=150,
        output_tokens=25,
        duration_seconds=Decimal("1.23"),
    )

    _upsert(s3_bucket)

    item = ddb_doc_metadata_table.get_item(Key={"fileName": "test-file"})["Item"]
    assert item[DocumentMetadata.PRECLASSIFICATION_BLUEPRINT_MATCHED_TYPE] == "W2"
    assert float(
        item[DocumentMetadata.PRECLASSIFICATION_BLUEPRINT_MATCH_CONFIDENCE]
    ) == pytest.approx(0.92)
    assert item[DocumentMetadata.PRECLASSIFICATION_BLUEPRINT_MATCH_INPUT_TOKENS] == 150
    assert item[DocumentMetadata.PRECLASSIFICATION_BLUEPRINT_MATCH_OUTPUT_TOKENS] == 25
    assert float(
        item[DocumentMetadata.PRECLASSIFICATION_BLUEPRINT_MATCH_DURATION_SECONDS]
    ) == pytest.approx(1.23)


def test_upsert_initial_ddb_record_stores_blueprint_no_match(
    ddb_doc_metadata_table, s3_bucket, lifecycle_mocks
):
    """When blueprint matcher finds no match, fields reflect that."""
    lifecycle_mocks[_Mock.PRECLASSIFY_DOCUMENT].return_value = BedrockClassificationResult(
        document_type="other_document", confidence=0.3, max_document_count_on_page=1
    )
    lifecycle_mocks[_Mock.FIND_MATCHING_BLUEPRINT].return_value = PreclassificationMatchResult(
        matched_document_type=None,
        confidence=0.0,
        input_tokens=120,
        output_tokens=18,
        duration_seconds=Decimal("0.95"),
    )

    _upsert(s3_bucket, user_provided_document_category=None)

    item = ddb_doc_metadata_table.get_item(Key={"fileName": "test-file"})["Item"]
    assert DocumentMetadata.PRECLASSIFICATION_BLUEPRINT_MATCHED_TYPE not in item
    assert float(
        item[DocumentMetadata.PRECLASSIFICATION_BLUEPRINT_MATCH_CONFIDENCE]
    ) == pytest.approx(0.0)
    assert item[DocumentMetadata.PRECLASSIFICATION_BLUEPRINT_MATCH_INPUT_TOKENS] == 120
    assert item[DocumentMetadata.PRECLASSIFICATION_BLUEPRINT_MATCH_OUTPUT_TOKENS] == 18
    assert float(
        item[DocumentMetadata.PRECLASSIFICATION_BLUEPRINT_MATCH_DURATION_SECONDS]
    ) == pytest.approx(0.95)


# =============================================================================
# Multipage document flagging (401)
# =============================================================================


def test_upsert_initial_ddb_record_flags_multipage_with_inconsistency(
    ddb_doc_metadata_table, s3_bucket, lifecycle_mocks
):
    """Multipage PDF where LLM detects inconsistency across pages is flagged as 401."""
    lifecycle_mocks[_Mock.GET_PAGE_COUNT].return_value = 2
    lifecycle_mocks[_Mock.IS_BLUR_DETECTION_ENABLED].return_value = False
    lifecycle_mocks[_Mock.PRECLASSIFY_DOCUMENT].return_value = BedrockClassificationResult(
        document_type="multipage",
        confidence=0.95,
        max_document_count_on_page=1,
        has_multipage_inconsistency=True,
    )

    _upsert(s3_bucket)

    item = ddb_doc_metadata_table.get_item(Key={"fileName": "test-file"})["Item"]
    assert item[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.MULTIPLE_DOCUMENTS_IN_MULTIPAGE
    assert DocumentMetadata.RESPONSE_JSON in item


def test_upsert_initial_ddb_record_multipage_flag_disabled_proceeds_to_bda(
    ddb_doc_metadata_table, s3_bucket, lifecycle_mocks
):
    """When flag is off, multipage doc with inconsistency proceeds normally."""
    lifecycle_mocks[_Mock.GET_PAGE_COUNT].return_value = 2
    lifecycle_mocks[_Mock.IS_BLUR_DETECTION_ENABLED].return_value = False
    lifecycle_mocks[_Mock.IS_MULTIPAGE_DOCUMENT_FLAGGING_ENABLED].return_value = False
    lifecycle_mocks[_Mock.PRECLASSIFY_DOCUMENT].return_value = BedrockClassificationResult(
        document_type="multipage",
        confidence=0.95,
        max_document_count_on_page=1,
        has_multipage_inconsistency=True,
    )

    _upsert(s3_bucket)

    item = ddb_doc_metadata_table.get_item(Key={"fileName": "test-file"})["Item"]
    assert item[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.NOT_STARTED


def test_upsert_initial_ddb_record_multipage_consistent_proceeds_to_bda(
    ddb_doc_metadata_table, s3_bucket, lifecycle_mocks
):
    """Multipage PDF with no inconsistency detected is NOT flagged."""
    lifecycle_mocks[_Mock.GET_PAGE_COUNT].return_value = 2
    lifecycle_mocks[_Mock.IS_BLUR_DETECTION_ENABLED].return_value = False
    lifecycle_mocks[_Mock.PRECLASSIFY_DOCUMENT].return_value = BedrockClassificationResult(
        document_type="W2",
        confidence=0.95,
        max_document_count_on_page=1,
        has_multipage_inconsistency=False,
    )

    _upsert(s3_bucket)

    item = ddb_doc_metadata_table.get_item(Key={"fileName": "test-file"})["Item"]
    assert item[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.NOT_STARTED


def test_upsert_initial_ddb_record_single_page_inconsistency_not_flagged(
    ddb_doc_metadata_table, s3_bucket, lifecycle_mocks
):
    """pages_detected=1 gates the check - has_multipage_inconsistency is ignored on single-page docs."""
    lifecycle_mocks[_Mock.IS_BLUR_DETECTION_ENABLED].return_value = False
    lifecycle_mocks[_Mock.PRECLASSIFY_DOCUMENT].return_value = BedrockClassificationResult(
        document_type="W2",
        confidence=0.95,
        max_document_count_on_page=1,
        has_multipage_inconsistency=True,
    )

    _upsert(s3_bucket)

    item = ddb_doc_metadata_table.get_item(Key={"fileName": "test-file"})["Item"]
    assert item[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.NOT_STARTED
