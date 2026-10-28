"""Tests for the extraction-compare router's status, access control, and cost breakdown."""

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
_CLAIMS = {"sub": "user-1", "cognito:groups": ["admin"]}
_OTHER_CLAIMS = {"sub": "user-2", "cognito:groups": ["admin"]}
_SUPER_ADMIN_CLAIMS = {"sub": "user-3", "cognito:groups": ["super-admin"]}


def _response(value: str) -> str:
    return json.dumps({"fields": {"name": {"value": value, "confidence": 0.9}}})


def _record(primary_method: str, responses: dict[str, str] | None = None) -> dict[str, Any]:
    return {
        DocumentMetadata.FILE_NAME: "doc.pdf",
        DocumentMetadata.IS_COMPARE: True,
        DocumentMetadata.TENANT_ID: "compare-user-1",
        DocumentMetadata.EXTRACT_METHOD: primary_method,
        DocumentMetadata.API_RESPONSES_BY_METHOD: (
            responses
            if responses is not None
            else {primary_method: _response("a"), _OCR_MAPPING: _response("b")}
        ),
    }


@pytest.fixture
def compare_mocks(mocker: Any) -> Callable[..., None]:
    def _apply(
        primary_method: str = ExtractMethod.TEXTRACT.value,
        by_reason: dict[str, dict[str, int]] | None = None,
        record: dict[str, Any] | None = None,
    ) -> None:
        mocker.patch(
            f"{_MODULE}.get_ddb_by_job_id",
            return_value=record if record is not None else _record(primary_method),
        )
        mocker.patch(f"{_MODULE}.sum_token_usage_by_model", return_value={})
        mocker.patch(f"{_MODULE}.get_token_usage_by_reason", return_value=by_reason or {})

    return _apply


def test_layout_fee_is_added_to_ocr_mapping_cost(compare_mocks):
    compare_mocks(ExtractMethod.TEXTRACT.value)

    result = get_compare_result(_CLAIMS, "job-1")

    assert result.is_completed is True
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

    result = get_compare_result(_CLAIMS, "job-1")

    assert result.cost_by_reason[LlmUsageReason.OCR_MAPPING] == pytest.approx(0.80 + _LAYOUT_FEE)


def test_layout_fee_is_not_in_shared_or_primary_cost(compare_mocks):
    compare_mocks(ExtractMethod.TEXTRACT.value)

    result = get_compare_result(_CLAIMS, "job-1")

    assert result.cost_by_reason["primary"] == pytest.approx(0.025)  # AnalyzeID only
    assert "shared" not in result.cost_by_reason


def test_pending_when_ocr_mapping_response_missing(compare_mocks):
    compare_mocks(
        record=_record(
            ExtractMethod.TEXTRACT.value, responses={ExtractMethod.TEXTRACT.value: _response("a")}
        )
    )

    result = get_compare_result(_CLAIMS, "job-1")

    assert result.is_completed is False


def test_not_found_when_job_missing(compare_mocks):
    compare_mocks(record={})

    with pytest.raises(HTTPException) as exc:
        get_compare_result(_CLAIMS, "job-1")

    assert exc.value.status_code == 404


def test_not_found_when_job_is_not_a_compare_job(compare_mocks):
    record = _record(ExtractMethod.TEXTRACT.value)
    record[DocumentMetadata.IS_COMPARE] = False
    compare_mocks(record=record)

    with pytest.raises(HTTPException) as exc:
        get_compare_result(_CLAIMS, "job-1")

    assert exc.value.status_code == 404


def test_not_found_for_another_users_compare_job(compare_mocks):
    compare_mocks(ExtractMethod.TEXTRACT.value)

    with pytest.raises(HTTPException) as exc:
        get_compare_result(_OTHER_CLAIMS, "job-1")

    assert exc.value.status_code == 404


def test_super_admin_can_read_any_compare_job(compare_mocks):
    compare_mocks(ExtractMethod.TEXTRACT.value)

    result = get_compare_result(_SUPER_ADMIN_CLAIMS, "job-1")

    assert result.is_completed is True
