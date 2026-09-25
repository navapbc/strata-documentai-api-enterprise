"""Tests for classifiers/document_classification.py classify_as_* functions."""

import pytest

from documentai_api.classifiers import document_classification as classification_util
from documentai_api.config.constants import ExtractMethod, ProcessStatus
from documentai_api.dtos.classification import ClassificationData
from documentai_api.dtos.ddb import UpdateDdbRecord
from documentai_api.dtos.extraction import ExtractionResult
from documentai_api.dtos.processing import InternalApiResponse
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.response_codes import ResponseCodes

_MODULE = "documentai_api.classifiers.document_classification"


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
        f"{_MODULE}.get_internal_api_response", return_value=fake_response
    )
    mock_update = mocker.patch(f"{_MODULE}.update_ddb")
    mocker.patch(f"{_MODULE}.finalize_v1_response")
    mocker.patch(f"{_MODULE}._is_compare", return_value=False)

    args = ["test-file", data]
    if error_msg:
        args.insert(1, error_msg)
    elif response_code == ResponseCodes.SUCCESS:
        args.insert(1, response_code)
        args.insert(3, ExtractMethod.BDA)

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
        f"{_MODULE}.get_internal_api_response", return_value=fake_response
    )
    mock_update = mocker.patch(f"{_MODULE}.update_ddb")
    mocker.patch(f"{_MODULE}.finalize_v1_response")
    mocker.patch(f"{_MODULE}._is_compare", return_value=False)

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


@pytest.mark.parametrize(
    ("function", "status"),
    [
        (
            classification_util.classify_as_no_document_detected,
            ProcessStatus.NO_DOCUMENT_DETECTED,
        ),
        (
            classification_util.classify_as_no_custom_blueprint_matched,
            ProcessStatus.NO_CUSTOM_BLUEPRINT_MATCHED,
        ),
    ],
)
def test_classify_as_no_match_writes_compare_response_and_falls_through(function, status, mocker):
    """Under compare mode the empty-response write is an addition; update_ddb must still run afterward."""
    data = ClassificationData(matched_document_class="paystub")
    fake_response = InternalApiResponse(
        validation_passed=True,
        document_category=None,
        matched_document_class=None,
        response_code="000",
        response_message="ok",
    )
    mocker.patch(f"{_MODULE}.get_internal_api_response", return_value=fake_response)
    mock_update = mocker.patch(f"{_MODULE}.update_ddb")
    mocker.patch(f"{_MODULE}.finalize_v1_response")
    mocker.patch(f"{_MODULE}._is_compare", return_value=True)
    mock_write_empty = mocker.patch(f"{_MODULE}._write_compare_empty_response")

    function("test-file", data)

    mock_write_empty.assert_called_once_with("test-file", status)
    mock_update.assert_called_once()


def test_classify_extraction_result_compare_mode_falls_through_to_classify_as_success(mocker):
    """Under compare mode _write_compare_v1_response is an addition; classify_as_success must still run."""
    result = ExtractionResult(document_type="paystub")
    mocker.patch(f"{_MODULE}.get_ddb_record", return_value={DocumentMetadata.IS_COMPARE: True})
    mock_write_compare = mocker.patch(f"{_MODULE}._write_compare_v1_response")
    mocker.patch(
        f"{_MODULE}.ClassificationData.from_extraction_result",
        return_value=ClassificationData(matched_document_class="paystub"),
    )
    mocker.patch(f"{_MODULE}.get_extraction_confidence_floor", return_value=0.5)
    mocker.patch(f"{_MODULE}.tenant_has_confidence_floor", return_value=True)
    mocker.patch(f"{_MODULE}.calculate_average_non_empty_confidence", return_value=0.9)
    mocker.patch(f"{_MODULE}.get_missing_required_fields", return_value=None)
    mock_success = mocker.patch(
        f"{_MODULE}.classify_as_success", return_value={"jobStatus": "completed"}
    )

    response = classification_util.classify_extraction_result(
        ddb_key="test-file",
        result=result,
        output_uri="s3://bucket/key",
        tenant_id="tenant",
    )

    mock_write_compare.assert_called_once()
    mock_success.assert_called_once()
    assert response == {"jobStatus": "completed"}
