from datetime import UTC, datetime
from decimal import Decimal

import pytest
from freezegun import freeze_time

from documentai_api.config.constants import ProcessStatus
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils import ddb as ddb_util
from documentai_api.utils.dto import (
    ClassificationData,
    InternalApiResponse,
    PreClassificationData,
    UpsertDdbData,
)
from documentai_api.utils.response_codes import ResponseCodes


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
        UpsertDdbData(
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
            pre_classification=PreClassificationData(
                document_type="W2",
                confidence=0.98,
            ),
            external_document_id="ext-doc-789",
            external_system_id="ext-sys-abc",
            ai_consent_flag=True,
        )
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
    assert item[DocumentMetadata.PRECLASSIFICATION_CATEGORY] == "W2"
    assert item[DocumentMetadata.PRECLASSIFICATION_CONFIDENCE] == Decimal("0.98")

    # external fields
    assert item[DocumentMetadata.EXTERNAL_DOCUMENT_ID] == "ext-doc-789"
    assert item[DocumentMetadata.EXTERNAL_SYSTEM_ID] == "ext-sys-abc"
    assert item[DocumentMetadata.AI_CONSENT_FLAG] is True

    # ttl stamped ~180 days out as an integer epoch
    ttl = item[DocumentMetadata.TIME_TO_LIVE]
    assert isinstance(ttl, Decimal)  # DynamoDB returns numbers as Decimal
    assert ttl % 1 == 0
    expected = int(datetime.now(UTC).timestamp()) + 180 * 24 * 60 * 60
    assert abs(int(ttl) - expected) < 600  # within 10 minutes


@freeze_time("2026-01-01 12:00:00+00:00")
def test_upsert_ddb_ttl_fixed_from_creation(ddb_doc_metadata_table):
    """TTL is stamped once at create and preserved on later upserts (not extended)."""
    object_key = "ttl-fixed-file"

    ddb_util.upsert_ddb(UpsertDdbData(object_key=object_key, original_file_name="f.pdf"))
    created_ttl = ddb_doc_metadata_table.get_item(Key={"fileName": object_key})["Item"][
        DocumentMetadata.TIME_TO_LIVE
    ]

    # a later upsert (simulated 5 days on) must not move the ttl
    with freeze_time("2026-01-06 12:00:00+00:00"):
        ddb_util.upsert_ddb(UpsertDdbData(object_key=object_key, original_file_name="f.pdf"))

    later_ttl = ddb_doc_metadata_table.get_item(Key={"fileName": object_key})["Item"][
        DocumentMetadata.TIME_TO_LIVE
    ]
    assert later_ttl == created_ttl


def test_upsert_ddb_consent_set_once_not_overwritten(ddb_doc_metadata_table):
    """AiConsentFlag is stamped on create and preserved on later upserts.

    A caller that opts out (False) at initial insert must not be silently
    flipped back to the True default by a later upsert that omits consent.
    """
    object_key = "consent-fixed-file"

    # initial insert opts out
    ddb_util.upsert_ddb(
        UpsertDdbData(object_key=object_key, original_file_name="f.pdf", ai_consent_flag=False)
    )
    assert (
        ddb_doc_metadata_table.get_item(Key={"fileName": object_key})["Item"][
            DocumentMetadata.AI_CONSENT_FLAG
        ]
        is False
    )

    # a later upsert that omits consent (defaults True) must not overwrite it
    ddb_util.upsert_ddb(UpsertDdbData(object_key=object_key, original_file_name="f.pdf"))
    assert (
        ddb_doc_metadata_table.get_item(Key={"fileName": object_key})["Item"][
            DocumentMetadata.AI_CONSENT_FLAG
        ]
        is False
    )


def test_upsert_ddb_consent_defaults_true(ddb_doc_metadata_table):
    """AiConsentFlag defaults to True when the caller omits it."""
    object_key = "consent-default-file"

    ddb_util.upsert_ddb(UpsertDdbData(object_key=object_key, original_file_name="f.pdf"))

    assert (
        ddb_doc_metadata_table.get_item(Key={"fileName": object_key})["Item"][
            DocumentMetadata.AI_CONSENT_FLAG
        ]
        is True
    )


def test_upsert_ddb_required_bools_always_written(ddb_doc_metadata_table):
    """isPasswordProtected/isDocumentBlurry always exist, defaulting to False.

    Callers that omit them must still get the attributes written (False), not
    a sparse item missing them.
    """
    object_key = "required-bools-file"

    ddb_util.upsert_ddb(UpsertDdbData(object_key=object_key, original_file_name="f.pdf"))

    item = ddb_doc_metadata_table.get_item(Key={"fileName": object_key})["Item"]
    assert item[DocumentMetadata.IS_PASSWORD_PROTECTED] is False
    assert item[DocumentMetadata.IS_DOCUMENT_BLURRY] is False
