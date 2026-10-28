"""Tests for the extraction-compare router's cost breakdown."""

import json
from collections.abc import Callable
from typing import Any

import pytest
from fastapi import HTTPException

from documentai_api.constants.processing import ExtractMethod, LlmUsageReason
from documentai_api.routers.extraction_compare import get_compare_result
from documentai_api.schemas.document_metadata import DocumentMetadata

_MODULE = "documentai_api.routers.extraction_compare"
_OCR_MAPPING = ExtractMethod.OCR_MAPPING.value
_NOVA_PRO = "us.amazon.nova-pro-v1:0"
_LAYOUT_FEE = 0.004  # AnalyzeDocument LAYOUT, one page


def _response(value: str) -> str:
    return json.dumps({"fields": {"name": {"value": value, "confidence": 0.9}}})


def _record(primary_method: str) -> dict[str, Any]:
    return {
        DocumentMetadata.FILE_NAME: "doc.pdf",
        DocumentMetadata.EXTRACT_METHOD: primary_method,
        DocumentMetadata.API_RESPONSES_BY_METHOD: {
            primary_method: _response("a"),
            _OCR_MAPPING: _response("b"),
        },
    }


@pytest.fixture
def compare_mocks(mocker: Any) -> Callable[..., None]:
    def _apply(primary_method: str, by_reason: dict[str, dict[str, int]] | None = None) -> None:
        mocker.patch(f"{_MODULE}.get_ddb_by_job_id", return_value=_record(primary_method))
        mocker.patch(f"{_MODULE}.sum_token_usage_by_model", return_value={})
        mocker.patch(f"{_MODULE}.get_token_usage_by_reason", return_value=by_reason or {})

    return _apply


def test_layout_fee_is_added_to_ocr_mapping_cost(compare_mocks):
    compare_mocks(ExtractMethod.TEXTRACT.value)

    result = get_compare_result("job-1")

    assert result.cost["analyze_document_layout"] == pytest.approx(_LAYOUT_FEE)
    assert result.cost_by_reason[LlmUsageReason.OCR_MAPPING] == pytest.approx(_LAYOUT_FEE)


def test_layout_fee_adds_to_ocr_mapping_token_cost(compare_mocks):
    compare_mocks(
        ExtractMethod.BDA.value,
        by_reason={
            f"{_NOVA_PRO}#{LlmUsageReason.OCR_MAPPING}": {
                "inputTokens": 1_000_000,
                "outputTokens": 0,
            }
        },
    )

    result = get_compare_result("job-1")

    assert result.cost_by_reason[LlmUsageReason.OCR_MAPPING] == pytest.approx(0.80 + _LAYOUT_FEE)


def test_layout_fee_is_not_in_shared_or_primary_cost(compare_mocks):
    compare_mocks(ExtractMethod.TEXTRACT.value)

    result = get_compare_result("job-1")

    assert result.cost_by_reason["primary"] == pytest.approx(0.025)  # AnalyzeID only
    assert "shared" not in result.cost_by_reason


def test_not_ready_when_ocr_mapping_response_missing(mocker):
    record = _record(ExtractMethod.TEXTRACT.value)
    del record[DocumentMetadata.API_RESPONSES_BY_METHOD][_OCR_MAPPING]
    mocker.patch(f"{_MODULE}.get_ddb_by_job_id", return_value=record)

    with pytest.raises(HTTPException) as exc:
        get_compare_result("job-1")

    assert exc.value.status_code == 404
