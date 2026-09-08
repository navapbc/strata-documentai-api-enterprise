from datetime import UTC, datetime
from decimal import Decimal

from documentai_api.processors.textract import process_textract_result


def test_process_textract_result_calls_classify_as_success(mocker):
    mock_classify = mocker.patch("documentai_api.utils.document_classification.classify_as_success")
    mocker.patch(
        "documentai_api.processors.textract.get_ddb_record", return_value={"tenantId": "t1"}
    )
    mocker.patch(
        "documentai_api.utils.document_classification.get_extraction_confidence_floor",
        return_value=0.65,
    )
    mocker.patch(
        "documentai_api.utils.document_classification.tenant_has_confidence_floor",
        return_value=False,
    )
    mocker.patch(
        "documentai_api.utils.document_classification.get_missing_required_fields",
        return_value=None,
    )

    from documentai_api.dtos.extraction import ExtractionResult

    result = ExtractionResult(
        document_type="US-drivers-licenses",
        output_uri="s3://bucket/output/textract/key.json",
        field_confidence_scores=[{"NAME_DETAILS.FIRST_NAME": 0.99}],
        field_empty_list=["ENDORSEMENTS"],
        extract_started_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        extract_completed_at=datetime(2025, 1, 1, 12, 0, 2, tzinfo=UTC),
        extract_time=Decimal("2.00"),
    )

    process_textract_result("test-key", result, "identity")

    mock_classify.assert_called_once()
    call_kwargs = mock_classify.call_args[1]
    assert call_kwargs["object_key"] == "test-key"
    assert call_kwargs["data"].matched_document_class == "US-drivers-licenses"
    assert call_kwargs["data"].field_empty_list == ["ENDORSEMENTS"]
    assert call_kwargs["data"].bda_output_s3_uri == "s3://bucket/output/textract/key.json"
    assert call_kwargs["below_extraction_confidence_floor"] is False  # 0.99 > 0.65


def test_process_textract_result_sets_below_floor_when_low_confidence(mocker):
    mock_classify = mocker.patch("documentai_api.utils.document_classification.classify_as_success")
    mocker.patch(
        "documentai_api.processors.textract.get_ddb_record", return_value={"tenantId": "t1"}
    )
    mocker.patch(
        "documentai_api.utils.document_classification.get_extraction_confidence_floor",
        return_value=0.90,
    )
    mocker.patch(
        "documentai_api.utils.document_classification.tenant_has_confidence_floor",
        return_value=False,
    )
    mocker.patch(
        "documentai_api.utils.document_classification.get_missing_required_fields",
        return_value=None,
    )

    from documentai_api.dtos.extraction import ExtractionResult

    result = ExtractionResult(
        document_type="US-drivers-licenses",
        output_uri="s3://bucket/output/textract/key.json",
        field_confidence_scores=[{"NAME_DETAILS.FIRST_NAME": 0.70}],
        field_empty_list=[],
        extract_started_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        extract_completed_at=datetime(2025, 1, 1, 12, 0, 2, tzinfo=UTC),
        extract_time=Decimal("2.00"),
    )

    process_textract_result("test-key", result, "identity")

    call_kwargs = mock_classify.call_args[1]
    assert call_kwargs["below_extraction_confidence_floor"] is True  # 0.70 < 0.90
