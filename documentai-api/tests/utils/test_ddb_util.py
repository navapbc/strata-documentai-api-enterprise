from datetime import UTC, datetime
from decimal import Decimal

import pytest
from freezegun import freeze_time

from documentai_api.config.constants import ProcessStatus
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils import ddb as ddb_util
from documentai_api.utils.dto import (
    BedrockClassificationResult,
    ClassificationData,
    InternalApiResponse,
)
from documentai_api.utils.response_codes import ResponseCodes


@pytest.mark.parametrize(
    ("arn", "expected_region"),
    [
        ("arn:aws:bedrock-data-automation:us-east-1:123456789012:job/abc123", "us-east-1"),
        ("arn:aws:bedrock-data-automation:eu-west-1:123456789012:job/xyz789", "eu-west-1"),
        ("invalid-arn", None),
    ],
)
def test_extract_region_from_bda_arn(arn, expected_region):
    """Test extracting AWS region from BDA ARN."""
    assert ddb_util.extract_region_from_bda_arn(arn) == expected_region


def test_get_elapsed_time_seconds():
    """Test elapsed time calculation."""
    year = datetime.now().year
    start = datetime(year, 1, 1, 12, 0, 0, tzinfo=UTC)
    end = datetime(year, 1, 1, 12, 0, 5, 500000, tzinfo=UTC)  # 5.5 seconds later

    result = ddb_util.get_elapsed_time_seconds(start, end)

    assert result == Decimal("5.5")
    assert isinstance(result, Decimal)


def test_calculate_bda_processing_times(ddb_doc_metadata_table):
    """Test BDA processing time calculation."""
    year = datetime.now().year
    created_at = datetime(year, 1, 1, 12, 0, 0, tzinfo=UTC)
    bda_started_at = datetime(year, 1, 1, 12, 0, 5, tzinfo=UTC)
    completion_time = datetime(year, 1, 1, 12, 0, 15, tzinfo=UTC)

    ddb_record = {
        DocumentMetadata.FILE_NAME: "test-file",
        DocumentMetadata.CREATED_AT: created_at.isoformat(),
        DocumentMetadata.BDA_STARTED_AT: bda_started_at.isoformat(),
    }

    ddb_doc_metadata_table.put_item(Item=ddb_record)

    result = ddb_util.calculate_bda_processing_times("test-file", completion_time)

    assert result.total_processing_time_seconds == Decimal("15.0")
    assert result.bda_processing_time_seconds == Decimal("10.0")


@freeze_time("2026-01-01 12:00:10+00:00")
def test_calculate_wait_time(ddb_doc_metadata_table):
    """Test BDA wait time calculation."""
    created_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

    ddb_record = {
        DocumentMetadata.FILE_NAME: "test-file",
        DocumentMetadata.CREATED_AT: created_at.isoformat(),
    }

    ddb_doc_metadata_table.put_item(Item=ddb_record)

    wait_time = ddb_util._calculate_wait_time("test-file")
    assert wait_time == Decimal("10.0")


@pytest.mark.parametrize(
    (
        "field_confidence_scores",
        "field_empty_list",
        "expected_count",
        "expected_non_empty",
        "expected_avg",
    ),
    [
        (None, None, 0, 0, None),
        ([], None, 0, 0, None),
        ([{"field1": 0.95}, {"field2": 0.85}], None, 2, 2, 0.9),
        ([{"field1": 0.95}, {"field2": 0.85}, {"field3": 0.75}], ["field3"], 3, 2, 0.9),
        ([{"field1": 0.8}], ["field1"], 1, 0, None),
    ],
)
def test_calculate_field_metrics(
    field_confidence_scores, field_empty_list, expected_count, expected_non_empty, expected_avg
):
    """Test field metrics calculation."""
    data = ClassificationData(
        field_confidence_scores=field_confidence_scores,
        field_empty_list=field_empty_list,
    )

    metrics = ddb_util._calculate_field_metrics(data)

    assert metrics.field_count == expected_count
    assert metrics.field_count_not_empty == expected_non_empty
    assert metrics.field_not_empty_avg_confidence == pytest.approx(expected_avg)


@pytest.mark.parametrize("has_bda_started_at", [True, False])
@freeze_time("2026-01-01 12:00:15+00:00")
def test_build_completion_timing(has_bda_started_at, ddb_doc_metadata_table, mocker):
    """Test completion timing updates."""
    ddb_record = {
        DocumentMetadata.FILE_NAME: "test-file",
        DocumentMetadata.CREATED_AT: datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC).isoformat(),
    }

    if has_bda_started_at:
        ddb_record[DocumentMetadata.BDA_STARTED_AT] = datetime(
            2026, 1, 1, 12, 0, 5, tzinfo=UTC
        ).isoformat()

    ddb_doc_metadata_table.put_item(Item=ddb_record)

    mock_get_modified = mocker.patch("documentai_api.utils.ddb.s3_service.get_last_modified_at")
    mock_get_modified.return_value = datetime(2026, 1, 1, 12, 0, 15, tzinfo=UTC)

    bda_output_s3_uri = "s3://bucket/key/job_metadata.json" if has_bda_started_at else None
    updates, values = ddb_util._build_completion_timing("test-file", bda_output_s3_uri)

    if has_bda_started_at:
        assert any(DocumentMetadata.BDA_COMPLETED_AT in u for u in updates)
        assert any(DocumentMetadata.PROCESSED_DATE in u for u in updates)
        assert ":bdaCompletedAt" in values
        assert ":processedDate" in values
        assert values[":totalProcessingTime"] == Decimal("15.0")
        assert values[":bdaProcessingTime"] == Decimal("10.0")
        mock_get_modified.assert_called_once_with("bucket", "key/job_metadata.json")
    else:
        assert updates == []
        assert values == {}
        mock_get_modified.assert_not_called()


@pytest.mark.parametrize(
    "status",
    [
        ProcessStatus.STARTED,
        ProcessStatus.SUCCESS,
        ProcessStatus.FAILED,
        ProcessStatus.PENDING_IMAGE_OPTIMIZATION,
    ],
)
@freeze_time("2026-01-01 12:00:10+00:00")
def test_build_timing_updates(status, ddb_doc_metadata_table, mocker):
    """Test timing updates for different statuses."""
    ddb_record = {
        DocumentMetadata.FILE_NAME: "test-file",
        DocumentMetadata.CREATED_AT: datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC).isoformat(),
    }

    if status in [ProcessStatus.SUCCESS, ProcessStatus.FAILED]:
        ddb_record[DocumentMetadata.BDA_STARTED_AT] = datetime(
            2026, 1, 1, 12, 0, 5, tzinfo=UTC
        ).isoformat()

    ddb_doc_metadata_table.put_item(Item=ddb_record)

    mock_get_modified = mocker.patch("documentai_api.utils.ddb.s3_service.get_last_modified_at")

    bda_output_s3_uri = (
        "s3://bucket/key/result.json"
        if status in [ProcessStatus.SUCCESS, ProcessStatus.FAILED]
        else None
    )

    if bda_output_s3_uri:
        mock_get_modified.return_value = datetime(2026, 1, 1, 12, 0, 10, tzinfo=UTC)

    updates, values = ddb_util._build_timing_updates("test-file", status, bda_output_s3_uri)

    if status == ProcessStatus.STARTED:
        assert DocumentMetadata.BDA_STARTED_AT in updates
        assert DocumentMetadata.BDA_WAIT_TIME_SECONDS in updates
        assert DocumentMetadata.BDA_COMPLETED_AT not in updates
        assert DocumentMetadata.PROCESSED_DATE not in updates
        assert values[":bdaWaitTimeSeconds"] == Decimal("10.0")
    elif status in [ProcessStatus.SUCCESS, ProcessStatus.FAILED]:
        assert DocumentMetadata.BDA_COMPLETED_AT in updates
        assert DocumentMetadata.PROCESSED_DATE in updates
        assert DocumentMetadata.BDA_STARTED_AT not in updates
        assert DocumentMetadata.BDA_WAIT_TIME_SECONDS not in updates
        assert values[":totalProcessingTime"] == Decimal("10.0")
        assert values[":bdaProcessingTime"] == Decimal("5.0")
    else:
        assert updates == ""
        assert values == {}


@pytest.mark.parametrize(
    ("internal_api_response", "v1_api_response", "bda_invocation_arn", "error_message"),
    [
        # all parameters populated. tests all 'if' paths
        (
            InternalApiResponse(
                validation_passed=True,
                document_category="income",
                matched_document_class="paystub",
                response_code=ResponseCodes.SUCCESS,
                response_message="Success",
            ),
            {"result": 200},
            "arn:aws:bedrock-data-automation:us-east-1:123:job/abc",
            "Test error message",
        ),
        # all parameters None/empty tests 'if' paths not executed
        (None, None, None, None),
    ],
)
def test_build_update_expression(
    internal_api_response, v1_api_response, bda_invocation_arn, error_message
):
    """Test update expression building."""
    data = ClassificationData(
        bda_output_s3_uri="s3://bucket/key",
        matched_blueprint_name="test-blueprint",
        matched_blueprint_confidence=0.95,
    )

    expr, values = ddb_util._build_update_expression(
        status=ProcessStatus.SUCCESS.value,
        data=data,
        internal_api_response=internal_api_response,
        v1_api_response=v1_api_response,
        bda_invocation_arn=bda_invocation_arn,
        error_message=error_message,
    )

    # confirm base fields are always present
    assert "SET" in expr
    assert DocumentMetadata.PROCESS_STATUS in expr
    assert ":processStatus" in values
    assert values[":processStatus"] == ProcessStatus.SUCCESS.value

    # verify attributes exist in update if populated, else attribute should not be present
    if internal_api_response:
        assert DocumentMetadata.RESPONSE_JSON in expr
        assert ":responseJson" in values
        assert DocumentMetadata.RESPONSE_CODE in expr
        assert ":responseCode" in values
    else:
        assert DocumentMetadata.RESPONSE_JSON not in expr
        assert ":responseJson" not in values
        assert DocumentMetadata.RESPONSE_CODE not in expr
        assert ":responseCode" not in values

    if v1_api_response:
        assert DocumentMetadata.V1_API_RESPONSE_JSON in expr
        assert ":v1ResponseJson" in values
    else:
        assert DocumentMetadata.V1_API_RESPONSE_JSON not in expr
        assert ":v1ResponseJson" not in values

    if bda_invocation_arn:
        assert DocumentMetadata.BDA_INVOCATION_ARN in expr
        assert ":bdaInvocationArn" in values
        assert DocumentMetadata.BDA_REGION_USED in expr
        assert ":bdaRegion" in values
    else:
        assert DocumentMetadata.BDA_INVOCATION_ARN not in expr
        assert ":bdaInvocationArn" not in values
        assert DocumentMetadata.BDA_REGION_USED not in expr
        assert ":bdaRegion" not in values

    if error_message:
        assert DocumentMetadata.ERROR_MESSAGE in expr
        assert ":errorMessage" in values
    else:
        assert DocumentMetadata.ERROR_MESSAGE not in expr
        assert ":errorMessage" not in values


def test_execute_ddb_update(ddb_doc_metadata_table):
    object_key = "table-key"
    item = {DocumentMetadata.FILE_NAME: object_key, "foo": "bar"}
    ddb_doc_metadata_table.put_item(Item=item)

    update_expression = "SET foo = :status"
    expression_values = {":status": "test"}

    ddb_util._execute_ddb_update(object_key, update_expression, expression_values)

    doc_meta_record = ddb_doc_metadata_table.get_item(Key={"fileName": object_key})["Item"]
    assert doc_meta_record["foo"] == "test"


@pytest.mark.parametrize("user_provided_document_category", ["income", None])
def test_get_user_provided_document_category(
    ddb_doc_metadata_table, user_provided_document_category
) -> str:
    item = {
        DocumentMetadata.FILE_NAME: "test-file",
        DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY: user_provided_document_category,
    }
    ddb_doc_metadata_table.put_item(Item=item)

    category = ddb_util.get_user_provided_document_category("test-file")
    assert category == user_provided_document_category


@pytest.mark.parametrize(
    "stored_value",
    [
        "Not specified",  # the default written by upsert_ddb when category is None
        "unknown",  # legacy fallback from older code paths
        "",  # empty string
        "totally_made_up",  # anything that isn't a real enum member
    ],
)
def test_get_user_provided_document_category_returns_none_for_invalid(
    ddb_doc_metadata_table, stored_value
):
    """Values not matching a DocumentCategory enum member should return None, not raise."""
    item = {
        DocumentMetadata.FILE_NAME: "test-file",
        DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY: stored_value,
    }
    ddb_doc_metadata_table.put_item(Item=item)

    assert ddb_util.get_user_provided_document_category("test-file") is None


def test_get_ddb_record(ddb_doc_metadata_table):
    item = {
        DocumentMetadata.FILE_NAME: "test-file",
        DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY: "income",
        DocumentMetadata.PROCESS_STATUS: "completed",
    }
    ddb_doc_metadata_table.put_item(Item=item)

    ddb_record = ddb_util.get_ddb_record("test-file")

    for k, v in item.items():
        assert ddb_record[k] == v


def test_get_ddb_by_job_id(ddb_doc_metadata_table):
    """Test getting DDB record by job ID."""
    job_id = "job-123"
    file_name = "test-file"
    ddb_record = {DocumentMetadata.JOB_ID: job_id, DocumentMetadata.FILE_NAME: file_name}
    ddb_doc_metadata_table.put_item(Item=ddb_record)

    result = ddb_util.get_ddb_by_job_id(job_id)

    for k, v in ddb_record.items():
        assert result[k] == v


@pytest.mark.parametrize(
    ("status", "has_timing"),
    [
        (ProcessStatus.SUCCESS.value, True),
        (ProcessStatus.STARTED.value, True),
        (ProcessStatus.NOT_STARTED.value, False),
    ],
)
def test_update_ddb(status, has_timing, ddb_doc_metadata_table, mocker):
    """Test DDB update."""
    import json

    internal_response = InternalApiResponse(
        validation_passed=True,
        document_category="income",
        matched_document_class="paystub",
        response_code=ResponseCodes.SUCCESS,
        response_message="Success",
    )
    data = ClassificationData(matched_document_class="paystub")

    mock_timing = mocker.patch("documentai_api.utils.ddb._build_timing_updates")
    mock_timing.return_value = ("timing = :t", {":t": "val"}) if has_timing else ("", {})

    mock_v1 = mocker.patch("documentai_api.utils.ddb.build_v1_api_response")
    mock_v1.return_value = {"status": "completed"}

    object_key = "test-file"

    ddb_util.update_ddb(object_key, status, internal_response, data)

    item = ddb_doc_metadata_table.get_item(Key={"fileName": object_key})["Item"]
    assert item[DocumentMetadata.PROCESS_STATUS] == status
    assert item[DocumentMetadata.V1_API_RESPONSE_JSON] == json.dumps(mock_v1.return_value)

    if has_timing:
        assert item["timing"] == "val"


def test_upsert_ddb(ddb_doc_metadata_table, mocker):
    """Test DDB insert with all fields."""
    mock_raw_metrics = mocker.MagicMock()
    mock_raw_metrics.to_json_dict.return_value = {"raw": "data"}
    mock_normalized_metrics = mocker.MagicMock()
    mock_normalized_metrics.to_json_dict.return_value = {"normalized": "data"}

    internal_response = InternalApiResponse(
        validation_passed=True,
        document_category="income",
        matched_document_class="paystub",
        response_code=ResponseCodes.SUCCESS,
        response_message="Success",
    )

    object_key = "test-file"

    ddb_util.upsert_ddb(
        object_key=object_key,
        original_file_name="original-test.pdf",
        user_provided_document_category="income",
        process_status=ProcessStatus.NOT_STARTED.value,
        internal_api_response=internal_response,
        file_size_bytes=1024,
        content_type="application/pdf",
        pages_detected=5,
        job_id="job-123",
        trace_id="trace-456",
        is_password_protected=True,
        is_document_blurry=False,
        pre_classification_document_type="W2",
        pre_classification_confidence=".98",
        external_document_id="ext-doc-789",
        external_system_id="ext-sys-abc",
        ai_consent_flag=True,
    )

    item = ddb_doc_metadata_table.get_item(Key={"fileName": object_key})["Item"]

    # base fields
    assert item[DocumentMetadata.FILE_NAME] == "test-file"
    assert item[DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY] == "income"
    assert item[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.NOT_STARTED.value
    assert item[DocumentMetadata.FILE_SIZE_BYTES] == 1024
    assert item[DocumentMetadata.CONTENT_TYPE] == "application/pdf"
    assert DocumentMetadata.CREATED_AT in item
    assert DocumentMetadata.UPDATED_AT in item

    # optional fields
    assert item[DocumentMetadata.PAGES_DETECTED] == 5
    assert item[DocumentMetadata.JOB_ID] == "job-123"
    assert item[DocumentMetadata.TRACE_ID] == "trace-456"
    assert item[DocumentMetadata.IS_PASSWORD_PROTECTED] is True
    assert item[DocumentMetadata.IS_DOCUMENT_BLURRY] is False
    assert DocumentMetadata.RESPONSE_JSON in item
    assert item[DocumentMetadata.PRE_CLASSIFICATION_DOCUMENT_TYPE] == "W2"
    assert item[DocumentMetadata.PRE_CLASSIFICATION_CONFIDENCE] == Decimal("0.98")

    # external fields
    assert item[DocumentMetadata.EXTERNAL_DOCUMENT_ID] == "ext-doc-789"
    assert item[DocumentMetadata.EXTERNAL_SYSTEM_ID] == "ext-sys-abc"
    assert item[DocumentMetadata.AI_CONSENT_FLAG] is True


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
    mocker.patch("documentai_api.utils.ddb.document_utils.get_page_count", return_value=1)
    mocker.patch(
        "documentai_api.utils.ddb.document_utils.is_password_protected",
        return_value=is_password_protected,
    )
    mock_preclassify = mocker.patch("documentai_api.utils.ddb.preclassify_document_image")
    if preclassify_result:
        mock_preclassify.return_value = preclassify_result

    mocker.patch("documentai_api.utils.ddb.get_bda_percentage", return_value=1.0)
    mocker.patch("documentai_api.utils.ddb.get_all_schemas", return_value={"W2": {}, "Payslip": {}})
    mocker.patch(
        "documentai_api.utils.ddb.build_v1_api_response", return_value={"status": "completed"}
    )

    s3_object = s3_bucket.put_object(
        Key="input/test-file",
        Body=b"bytes",
        ContentType=content_type,
    )

    ddb_util.upsert_initial_ddb_record(
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
        assert (
            item[DocumentMetadata.PRE_CLASSIFICATION_DOCUMENT_TYPE]
            == preclassify_result.document_type
        )

    if has_internal_response:
        assert DocumentMetadata.RESPONSE_JSON in item
        assert DocumentMetadata.V1_API_RESPONSE_JSON in item
    else:
        assert DocumentMetadata.RESPONSE_JSON not in item


def test_set_bda_processing_status_started(mocker):
    """Test setting BDA status to started."""
    mock_update = mocker.patch("documentai_api.utils.ddb.update_ddb")

    ddb_util.set_bda_processing_status_started("test-file", "arn:aws:bda:us-east-1:123:job/1")

    mock_update.assert_called_once_with(
        object_key="test-file",
        status=ProcessStatus.STARTED,
        internal_api_response=None,
        bda_invocation_arn="arn:aws:bda:us-east-1:123:job/1",
    )


def test_set_bda_processing_status_not_started(mocker):
    """Test setting BDA status to not started."""
    mock_update = mocker.patch("documentai_api.utils.ddb.update_ddb")

    ddb_util.set_bda_processing_status_not_started("test-file")

    mock_update.assert_called_once_with(
        object_key="test-file",
        status=ProcessStatus.NOT_STARTED,
        internal_api_response=None,
    )


# test all classify_as* methods - classify_as_success, classify_as_failed, etc.
# the structure is essentially the identical, test using parameterization rather
# than repeating boilerplate code each time
@pytest.mark.parametrize(
    ("function", "response_code", "status", "matched_document_class", "error_msg"),
    [
        (
            ddb_util.classify_as_success,
            ResponseCodes.SUCCESS,
            ProcessStatus.SUCCESS,
            "paystub",
            None,
        ),
        (
            ddb_util.classify_as_failed,
            ResponseCodes.INTERNAL_PROCESSING_ERROR,
            ProcessStatus.FAILED,
            None,
            "Test error",
        ),
        (
            ddb_util.classify_as_not_implemented,
            ResponseCodes.DOCUMENT_TYPE_NOT_IMPLEMENTED,
            ProcessStatus.SUCCESS,
            None,
            None,
        ),
        (
            ddb_util.classify_as_no_document_detected,
            ResponseCodes.NO_DOCUMENT_DETECTED,
            ProcessStatus.NO_DOCUMENT_DETECTED,
            None,
            None,
        ),
        (
            ddb_util.classify_as_no_custom_blueprint_matched,
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

    mock_get_response = mocker.patch("documentai_api.utils.ddb.get_internal_api_response")
    mock_update = mocker.patch("documentai_api.utils.ddb.update_ddb")

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

    mock_update.assert_called_once_with(**expected_call)


def test_classify_as_ai_consent_declined(mocker):
    """Test classify_as_ai_consent_declined marks file correctly."""
    mock_get_response = mocker.patch("documentai_api.utils.ddb.get_internal_api_response")
    mock_update = mocker.patch("documentai_api.utils.ddb.update_ddb")

    ddb_util.classify_as_ai_consent_declined("test-file")

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
# Batch DDB integration tests (moto-backed)
# =============================================================================


@pytest.mark.integration
class TestCreateBatch:
    def test_creates_record_with_tenant(self, ddb_batches_table):
        """create_batch writes tenantId and clientName to DDB."""
        from documentai_api.schemas.document_batches import DocumentBatches

        ddb_util.create_batch(
            "batch-1",
            3,
            None,
            tenant_id="tenant-abc",
            api_key_name="client-xyz",
        )

        item = ddb_batches_table.get_item(Key={"batchId": "batch-1"})["Item"]
        assert item[DocumentBatches.TENANT_ID] == "tenant-abc"
        assert item[DocumentBatches.API_KEY_NAME] == "client-xyz"
        assert item[DocumentBatches.BATCH_STATUS] == "uploading"
        assert item[DocumentBatches.TOTAL_FILES] == 3

    def test_returns_created_at_timestamp(self, ddb_batches_table):
        """create_batch returns the createdAt ISO timestamp."""
        from datetime import datetime

        created_at = ddb_util.create_batch("batch-2", 1, None)
        assert created_at is not None
        datetime.fromisoformat(created_at)

    def test_duplicate_batch_id_raises_409(self, ddb_batches_table):
        """create_batch with existing batch_id raises HTTPException 409."""
        from fastapi import HTTPException

        ddb_util.create_batch("batch-dup", 1, None)

        with pytest.raises(HTTPException) as exc_info:
            ddb_util.create_batch("batch-dup", 2, None)

        assert exc_info.value.status_code == 409
        assert "already exists" in exc_info.value.detail


@pytest.mark.integration
class TestUpdateBatchStatus:
    def test_updates_status(self, ddb_batches_table):
        """update_batch_status changes the batch status."""
        from documentai_api.config.constants import BatchStatus
        from documentai_api.schemas.document_batches import DocumentBatches

        ddb_util.create_batch("batch-u1", 1, None)
        ddb_util.update_batch_status("batch-u1", status=BatchStatus.PROCESSING)

        item = ddb_batches_table.get_item(Key={"batchId": "batch-u1"})["Item"]
        assert item[DocumentBatches.BATCH_STATUS] == BatchStatus.PROCESSING.value

    def test_conditional_update_succeeds(self, ddb_batches_table):
        """Conditional update succeeds when condition matches."""
        from documentai_api.config.constants import BatchStatus
        from documentai_api.schemas.document_batches import DocumentBatches

        ddb_util.create_batch("batch-c1", 1, None)
        ddb_util.update_batch_status("batch-c1", status=BatchStatus.PROCESSING)

        ddb_util.update_batch_status(
            "batch-c1",
            status=BatchStatus.COMPLETED,
            condition_expression=f"{DocumentBatches.BATCH_STATUS} = :expected",
            condition_values={":expected": BatchStatus.PROCESSING.value},
        )

        item = ddb_batches_table.get_item(Key={"batchId": "batch-c1"})["Item"]
        assert item[DocumentBatches.BATCH_STATUS] == BatchStatus.COMPLETED.value

    def test_conditional_update_fails_on_mismatch(self, ddb_batches_table):
        """Conditional update raises when condition doesn't match (race lost)."""
        from botocore.exceptions import ClientError

        from documentai_api.config.constants import BatchStatus
        from documentai_api.schemas.document_batches import DocumentBatches

        ddb_util.create_batch("batch-c2", 1, None)
        ddb_util.update_batch_status("batch-c2", status=BatchStatus.COMPLETED)

        with pytest.raises(ClientError) as exc_info:
            ddb_util.update_batch_status(
                "batch-c2",
                status=BatchStatus.FAILED,
                condition_expression=f"{DocumentBatches.BATCH_STATUS} = :expected",
                condition_values={":expected": BatchStatus.PROCESSING.value},
            )

        assert exc_info.value.response["Error"]["Code"] == "ConditionalCheckFailedException"


@pytest.mark.integration
class TestQueryJobsByBatchId:
    def test_returns_jobs_for_batch(self, ddb_doc_metadata_table):
        """query_jobs_by_batch_id returns all jobs associated with a batch."""
        ddb_util.upsert_ddb(
            object_key="0-file1.pdf",
            original_file_name="file1.pdf",
            process_status=ProcessStatus.SUCCESS.value,
            job_id="job-1",
            batch_id="batch-q1",
        )
        ddb_util.upsert_ddb(
            object_key="1-file2.pdf",
            original_file_name="file2.pdf",
            process_status=ProcessStatus.STARTED.value,
            job_id="job-2",
            batch_id="batch-q1",
        )
        ddb_util.upsert_ddb(
            object_key="0-file3.pdf",
            original_file_name="file3.pdf",
            process_status=ProcessStatus.SUCCESS.value,
            job_id="job-3",
            batch_id="batch-other",
        )

        results = ddb_util.query_jobs_by_batch_id("batch-q1")

        assert len(results) == 2
        job_ids = {r["jobId"] for r in results}
        assert job_ids == {"job-1", "job-2"}

    def test_returns_empty_for_nonexistent_batch(self, ddb_doc_metadata_table):
        """query_jobs_by_batch_id returns empty list for unknown batch."""
        results = ddb_util.query_jobs_by_batch_id("batch-nonexistent")
        assert results == []


@pytest.mark.integration
class TestGetBatch:
    def test_returns_record(self, ddb_batches_table):
        """get_batch returns the batch record."""
        from documentai_api.schemas.document_batches import DocumentBatches

        ddb_util.create_batch("batch-g1", 5, None, tenant_id="t1", api_key_name="c1")

        record = ddb_util.get_batch("batch-g1")

        assert record is not None
        assert record[DocumentBatches.BATCH_ID] == "batch-g1"
        assert record[DocumentBatches.TENANT_ID] == "t1"

    def test_returns_none_for_missing(self, ddb_batches_table):
        """get_batch returns None for nonexistent batch."""
        assert ddb_util.get_batch("batch-missing") is None
