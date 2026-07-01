import pytest

from documentai_api.config.constants import ProcessStatus
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils import document_lifecycle as lifecycle_util
from documentai_api.utils.dto import BedrockClassificationResult, ClassificationData
from documentai_api.utils.response_codes import ResponseCodes


@pytest.mark.parametrize(
    (
        "user_provided_document_category",
        "content_type",
        "is_password_protected",
        "preclassify_result",
        "expected_status",
        "has_internal_response",
    ),
    [
        ("income", "application/pdf", True, None, ProcessStatus.PASSWORD_PROTECTED, True),
        (
            "income",
            "application/pdf",
            False,
            BedrockClassificationResult(
                document_type="other_document",
                confidence=0.3,
                document_count=1,
                is_document=True,
                is_blurry=True,
            ),
            ProcessStatus.BLURRY_DOCUMENT_DETECTED,
            True,
        ),
        (
            "income",
            "application/pdf",
            False,
            BedrockClassificationResult(
                document_type="not_a_document",
                confidence=0.9,
                document_count=1,
                is_document=False,
                is_blurry=False,
            ),
            ProcessStatus.NO_DOCUMENT_DETECTED,
            True,
        ),
        (
            "income",
            "application/pdf",
            False,
            BedrockClassificationResult(
                document_type="W2",
                confidence=0.95,
                document_count=2,
                is_document=True,
                is_blurry=False,
            ),
            ProcessStatus.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
            True,
        ),
        (
            "income",
            "image/jpeg",
            False,
            BedrockClassificationResult(
                document_type="W2",
                confidence=0.95,
                document_count=1,
                is_document=True,
                is_blurry=False,
            ),
            ProcessStatus.PENDING_IMAGE_OPTIMIZATION,
            False,
        ),
        (
            "income",
            "application/pdf",
            False,
            BedrockClassificationResult(
                document_type="W2",
                confidence=0.95,
                document_count=1,
                is_document=True,
                is_blurry=False,
            ),
            ProcessStatus.NOT_STARTED,
            False,
        ),
        (
            None,
            "application/pdf",
            False,
            BedrockClassificationResult(
                document_type="W2",
                confidence=0.95,
                document_count=1,
                is_document=True,
                is_blurry=False,
            ),
            ProcessStatus.NOT_STARTED,
            False,
        ),
    ],
)
def test_upsert_initial_ddb_record(
    ddb_doc_metadata_table,
    s3_bucket,
    user_provided_document_category,
    content_type,
    is_password_protected,
    preclassify_result,
    expected_status,
    has_internal_response,
    mocker,
):
    mocker.patch(
        "documentai_api.utils.document_lifecycle.document_utils.get_page_count", return_value=1
    )
    mocker.patch(
        "documentai_api.utils.document_lifecycle.document_utils.is_password_protected",
        return_value=is_password_protected,
    )
    mock_preclassify = mocker.patch("documentai_api.utils.document_lifecycle.preclassify_document")
    if preclassify_result:
        mock_preclassify.return_value = preclassify_result

    mocker.patch(
        "documentai_api.utils.ddb.build_v1_api_response",
        return_value={"status": "completed"},
    )

    s3_object = s3_bucket.put_object(
        Key="input/test-file",
        Body=b"bytes",
        ContentType=content_type,
    )

    lifecycle_util.upsert_initial_ddb_record(
        source_bucket_name=s3_object.bucket_name,
        source_object_key=s3_object.key,
        original_file_name="original-test.pdf",
        ddb_key="test-file",
        user_provided_document_category=user_provided_document_category,
        job_id="test-job-id",
        trace_id="test-trace-id",
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

    if preclassify_result:
        assert item[DocumentMetadata.PRECLASSIFICATION_CATEGORY] == preclassify_result.document_type

    if has_internal_response:
        assert DocumentMetadata.RESPONSE_JSON in item
        assert DocumentMetadata.V1_API_RESPONSE_JSON in item
    else:
        assert DocumentMetadata.RESPONSE_JSON not in item


def test_set_bda_processing_status_started(mocker):
    """Test setting BDA status to started."""
    mock_update = mocker.patch("documentai_api.utils.document_lifecycle.update_ddb")

    lifecycle_util.set_bda_processing_status_started(
        "test-file", "arn:aws:bda:us-east-1:123:job/1", "arn:aws:project/123"
    )

    mock_update.assert_called_once_with(
        object_key="test-file",
        status=ProcessStatus.STARTED,
        internal_api_response=None,
        bda_invocation_arn="arn:aws:bda:us-east-1:123:job/1",
        bda_project_arn_used="arn:aws:project/123",
        pages_sent_to_bda=None,
    )


def test_set_bda_processing_status_not_started(mocker):
    """Test setting BDA status to not started."""
    mock_update = mocker.patch("documentai_api.utils.document_lifecycle.update_ddb")

    lifecycle_util.set_bda_processing_status_not_started("test-file")

    mock_update.assert_called_once_with(
        object_key="test-file",
        status=ProcessStatus.NOT_STARTED,
        internal_api_response=None,
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
    """No record to claim (never upserted) → conditional update fails, returns False."""
    claimed = lifecycle_util.set_processing_status_started(
        "does-not-exist", ProcessStatus.PENDING_IMAGE_OPTIMIZATION.value
    )

    assert claimed is False


# test all classify_as* methods - classify_as_success, classify_as_failed, etc.
# the structure is essentially the identical, test using parameterization rather
# than repeating boilerplate code each time
@pytest.mark.parametrize(
    ("function", "response_code", "status", "matched_document_class", "error_msg"),
    [
        (
            lifecycle_util.classify_as_success,
            ResponseCodes.SUCCESS,
            ProcessStatus.SUCCESS,
            "paystub",
            None,
        ),
        (
            lifecycle_util.classify_as_failed,
            ResponseCodes.INTERNAL_PROCESSING_ERROR,
            ProcessStatus.FAILED,
            None,
            "Test error",
        ),
        (
            lifecycle_util.classify_as_not_implemented,
            ResponseCodes.DOCUMENT_TYPE_NOT_IMPLEMENTED,
            ProcessStatus.SUCCESS,
            None,
            None,
        ),
        (
            lifecycle_util.classify_as_no_document_detected,
            ResponseCodes.NO_DOCUMENT_DETECTED,
            ProcessStatus.NO_DOCUMENT_DETECTED,
            None,
            None,
        ),
        (
            lifecycle_util.classify_as_no_custom_blueprint_matched,
            ResponseCodes.DOCUMENT_TYPE_NOT_IMPLEMENTED,
            ProcessStatus.NO_CUSTOM_BLUEPRINT_MATCHED,
            None,
            None,
        ),
    ],
)
def test_classify_functions(
    function, response_code, status, matched_document_class, error_msg, mocker
):
    """Test all classify_as_* functions."""
    data = ClassificationData(matched_document_class="paystub")

    mock_get_response = mocker.patch(
        "documentai_api.utils.document_lifecycle.get_internal_api_response"
    )
    mock_update = mocker.patch("documentai_api.utils.document_lifecycle.update_ddb")

    # all classify functions require an object key and classification data
    args = ["test-file", data]

    # classify as failure requires an error message as the second argument
    if error_msg:
        args.insert(1, error_msg)

    # classify as success requires response_code as the second argument
    elif response_code == ResponseCodes.SUCCESS:
        args.insert(1, response_code)

    function(*args)

    mock_get_response.assert_called_once_with(
        object_key="test-file",
        response_code=response_code,
        matched_document_class=matched_document_class,
    )

    expected_call = {
        "object_key": "test-file",
        "status": status,
        "internal_api_response": mock_get_response.return_value,
        "data": data,
    }

    if error_msg:
        expected_call["error_message"] = error_msg

    if function == lifecycle_util.classify_as_success:
        expected_call["below_extraction_confidence_floor"] = False
        expected_call["result_processor_started_at"] = None

    if function in (
        lifecycle_util.classify_as_failed,
        lifecycle_util.classify_as_no_document_detected,
        lifecycle_util.classify_as_no_custom_blueprint_matched,
    ):
        expected_call["result_processor_started_at"] = None

    mock_update.assert_called_once_with(**expected_call)


def test_classify_as_ai_consent_declined(mocker):
    """Test classify_as_ai_consent_declined marks file correctly."""
    mock_get_response = mocker.patch(
        "documentai_api.utils.document_lifecycle.get_internal_api_response"
    )
    mock_update = mocker.patch("documentai_api.utils.document_lifecycle.update_ddb")

    lifecycle_util.classify_as_ai_consent_declined("test-file")

    mock_get_response.assert_called_once_with(
        object_key="test-file",
        response_code=ResponseCodes.AI_CONSENT_DECLINED,
        matched_document_class=None,
    )
    mock_update.assert_called_once_with(
        object_key="test-file",
        status=ProcessStatus.AI_CONSENT_DECLINED,
        internal_api_response=mock_get_response.return_value,
    )


# =============================================================================
# Textract identity routing
# =============================================================================


def test_upsert_initial_ddb_record_routes_to_textract_when_enabled(
    ddb_doc_metadata_table,
    s3_bucket,
    mocker,
):
    """When textract flag is on and preclassification = identity_verification, routes to Textract."""
    mocker.patch(
        "documentai_api.utils.document_lifecycle.document_utils.get_page_count", return_value=1
    )
    mocker.patch(
        "documentai_api.utils.document_lifecycle.document_utils.is_password_protected",
        return_value=False,
    )
    mocker.patch(
        "documentai_api.utils.document_lifecycle.preclassify_document",
        return_value=BedrockClassificationResult(
            document_type="identity_verification",
            confidence=0.95,
            document_count=1,
            is_document=True,
            is_blurry=False,
        ),
    )

    mock_textract = mocker.patch(
        "documentai_api.utils.document_lifecycle.try_textract_identity",
        return_value={
            "matched_document_class": "US-drivers-licenses",
            "field_confidence_scores": [{"NAME_DETAILS.FIRST_NAME": 0.99}],
            "textract_s3_uri": "s3://test-bucket/output/textract/test-file.json",
            "extract_started_at": "2025-01-01T00:00:00+00:00",
            "extract_completed_at": "2025-01-01T00:00:02+00:00",
            "extract_time": "2.00",
        },
    )
    mock_finalize = mocker.patch("documentai_api.utils.document_lifecycle.finalize_textract_result")

    s3_bucket.put_object(Key="input/test-file", Body=b"bytes", ContentType="image/jpeg")

    lifecycle_util.upsert_initial_ddb_record(
        source_bucket_name="test-bucket",
        source_object_key="input/test-file",
        original_file_name="license.jpg",
        ddb_key="test-file",
        user_provided_document_category="identity",
        job_id="test-job-id",
        trace_id="test-trace-id",
    )

    mock_textract.assert_called_once()
    mock_finalize.assert_called_once_with("test-file", mock_textract.return_value, "identity")

    item = ddb_doc_metadata_table.get_item(Key={"fileName": "test-file"})["Item"]
    assert item[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.STARTED


def test_upsert_initial_ddb_record_falls_through_when_textract_returns_none(
    ddb_doc_metadata_table,
    s3_bucket,
    mocker,
):
    """When textract returns None (flag off or failure), falls through to BDA path."""
    mocker.patch(
        "documentai_api.utils.document_lifecycle.document_utils.get_page_count", return_value=1
    )
    mocker.patch(
        "documentai_api.utils.document_lifecycle.document_utils.is_password_protected",
        return_value=False,
    )
    mocker.patch(
        "documentai_api.utils.document_lifecycle.preclassify_document",
        return_value=BedrockClassificationResult(
            document_type="identity_verification",
            confidence=0.95,
            document_count=1,
            is_document=True,
            is_blurry=False,
        ),
    )
    mocker.patch(
        "documentai_api.utils.document_lifecycle.try_textract_identity",
        return_value=None,
    )
    mock_finalize = mocker.patch("documentai_api.utils.document_lifecycle.finalize_textract_result")

    s3_bucket.put_object(Key="input/test-file", Body=b"bytes", ContentType="image/jpeg")

    lifecycle_util.upsert_initial_ddb_record(
        source_bucket_name="test-bucket",
        source_object_key="input/test-file",
        original_file_name="license.jpg",
        ddb_key="test-file",
        user_provided_document_category="identity",
        job_id="test-job-id",
        trace_id="test-trace-id",
    )

    mock_finalize.assert_not_called()

    item = ddb_doc_metadata_table.get_item(Key={"fileName": "test-file"})["Item"]
    # JPEG -> goes to image optimization, not Textract
    assert item[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.PENDING_IMAGE_OPTIMIZATION
