"""Tests for pipeline/bda.py _classify dispatch logic."""

import pytest

from documentai_api.config.constants import ProcessStatus
from documentai_api.dtos.classification import ClassificationData
from documentai_api.dtos.extraction import ExtractionResult
from documentai_api.dtos.processing import ProcessorResult
from documentai_api.pipeline.bda import _classify

_MODULE = "documentai_api.pipeline.bda"


def test_classify_dispatches_to_classify_extraction_result_when_extraction_result_present(mocker):
    mock = mocker.patch(
        f"{_MODULE}.classify_extraction_result", return_value={"jobStatus": "completed"}
    )
    result = ProcessorResult(
        object_key="tenant/file.pdf",
        tenant_id="tenant",
        batch_id="batch-1",
        result_processor_started_at="2024-01-01T00:00:00",
        extraction_result=ExtractionResult(document_type="passport", output_uri="s3://bucket/key"),
    )

    response = _classify(result)

    mock.assert_called_once_with(
        ddb_key="tenant/file.pdf",
        result=result.extraction_result,
        tenant_id="tenant",
        batch_id="batch-1",
        result_processor_started_at="2024-01-01T00:00:00",
    )
    assert response == {"jobStatus": "completed"}


def test_classify_dispatches_to_no_custom_blueprint_matched(mocker):
    mock = mocker.patch(
        f"{_MODULE}.classify_as_no_custom_blueprint_matched",
        return_value={"jobStatus": "completed"},
    )
    data = ClassificationData(additional_info="no match")
    result = ProcessorResult(
        object_key="tenant/file.pdf",
        batch_id="batch-1",
        result_processor_started_at="2024-01-01T00:00:00",
        status=ProcessStatus.NO_CUSTOM_BLUEPRINT_MATCHED,
        classification_data=data,
    )

    _classify(result)

    mock.assert_called_once_with(
        object_key="tenant/file.pdf",
        data=data,
        result_processor_started_at="2024-01-01T00:00:00",
        batch_id="batch-1",
    )


def test_classify_dispatches_to_no_document_detected_for_other_status(mocker):
    mock = mocker.patch(
        f"{_MODULE}.classify_as_no_document_detected", return_value={"jobStatus": "completed"}
    )
    data = ClassificationData(additional_info="no doc")
    result = ProcessorResult(
        object_key="tenant/file.pdf",
        batch_id=None,
        result_processor_started_at=None,
        status=ProcessStatus.NO_DOCUMENT_DETECTED,
        classification_data=data,
    )

    _classify(result)

    mock.assert_called_once_with(
        object_key="tenant/file.pdf",
        data=data,
        result_processor_started_at=None,
        batch_id=None,
    )


def test_classify_raises_when_no_extraction_result_or_status():
    result = ProcessorResult(object_key="tenant/file.pdf")

    with pytest.raises(ValueError, match="no extraction_result or status"):
        _classify(result)
