"""Tests for the LLM extractor."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from documentai_api.extractors.llm import compute_confidence, ocr_blocks_to_text, run_llm_extraction

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

LINE_BLOCK = {
    "BlockType": "LINE",
    "Text": "John Smith",
    "Geometry": {"BoundingBox": {"Left": 0.1, "Top": 0.1, "Width": 0.3, "Height": 0.05}},
}

WORD_BLOCK = {
    "BlockType": "WORD",
    "Text": "John",
    "Confidence": 99.0,
    "Geometry": {"BoundingBox": {"Left": 0.1, "Top": 0.1, "Width": 0.1, "Height": 0.05}},
}

WORD_BLOCK_2 = {
    "BlockType": "WORD",
    "Text": "Smith",
    "Confidence": 95.0,
    "Geometry": {"BoundingBox": {"Left": 0.25, "Top": 0.1, "Width": 0.1, "Height": 0.05}},
}

OCR_BLOCKS: list[dict[str, Any]] = [LINE_BLOCK, WORD_BLOCK, WORD_BLOCK_2]


# ---------------------------------------------------------------------------
# compute_confidence
# ---------------------------------------------------------------------------


def test_compute_confidence_empty_citation():
    assert compute_confidence(None, OCR_BLOCKS) == 0.0
    assert compute_confidence("", OCR_BLOCKS) == 0.0
    assert compute_confidence("   ", OCR_BLOCKS) == 0.0


def test_compute_confidence_no_matching_line():
    assert compute_confidence("zzz totally unrelated", OCR_BLOCKS) == 0.0


def test_compute_confidence_returns_word_avg_for_match():
    conf = compute_confidence("John Smith", OCR_BLOCKS)
    expected = round((99.0 + 95.0) / 2 / 100.0, 4)
    assert conf == expected


def test_compute_confidence_falls_back_to_ratio_when_no_word_blocks():
    blocks = [LINE_BLOCK]  # no WORD blocks
    conf = compute_confidence("John Smith", blocks)
    assert 0.0 < conf <= 1.0


def test_compute_confidence_no_bounding_box_falls_back_to_ratio():
    line_no_bb = {"BlockType": "LINE", "Text": "John Smith", "Geometry": {}}
    conf = compute_confidence("John Smith", [line_no_bb])
    assert 0.0 < conf <= 1.0


# ---------------------------------------------------------------------------
# ocr_blocks_to_text
# ---------------------------------------------------------------------------


def test_ocr_blocks_to_text_joins_lines():
    blocks = [
        {"BlockType": "LINE", "Text": "First line"},
        {"BlockType": "WORD", "Text": "ignored"},
        {"BlockType": "LINE", "Text": "Second line"},
    ]
    assert ocr_blocks_to_text(blocks) == "First line\nSecond line"


def test_ocr_blocks_to_text_skips_empty_text():
    blocks = [
        {"BlockType": "LINE", "Text": ""},
        {"BlockType": "LINE", "Text": "Real line"},
    ]
    assert ocr_blocks_to_text(blocks) == "Real line"


def test_ocr_blocks_to_text_empty_blocks():
    assert ocr_blocks_to_text([]) == ""


# ---------------------------------------------------------------------------
# run_llm_extraction
# ---------------------------------------------------------------------------


def _make_field_response(value: str, citation: str) -> MagicMock:
    m = MagicMock()
    m.value = value
    m.text_citation = citation
    return m


def test_run_llm_extraction_success(mocker):
    from documentai_api.utils.schemas import DocumentSchema, SchemaField

    schema = DocumentSchema(
        document_type="payslip",
        description="Payslip",
        fields=[SchemaField(name="employee_name", type="string", description="Employee name")],
    )

    mock_response = MagicMock()
    mock_response.employee_name = _make_field_response("John Smith", "John Smith")

    mock_completion = MagicMock()
    mock_completion.usage.input_tokens = 100
    mock_completion.usage.output_tokens = 50

    mocker.patch(
        "documentai_api.utils.ssm.get_llm_extractor_model_id",
        return_value="us.amazon.nova-pro-v1:0",
    )
    mocker.patch("documentai_api.utils.schemas.get_document_schema", return_value=schema)

    mock_client = MagicMock()
    mock_client.chat.completions.create_with_completion.return_value = (
        mock_response,
        mock_completion,
    )
    mocker.patch("instructor.from_bedrock", return_value=mock_client)
    mocker.patch(
        "documentai_api.services.aws_client_factory.AWSClientFactory.get_bedrock_runtime_client",
        return_value=MagicMock(),
    )

    mock_telemetry = mocker.patch("documentai_api.extractors.llm._write_llm_telemetry")

    result = run_llm_extraction(
        ddb_key="doc.json",
        document_type="payslip",
        ocr_blocks=OCR_BLOCKS,
    )

    assert result.document_type == "payslip"
    assert len(result.field_confidence_scores) == 1
    mock_telemetry.assert_called_once()


def test_run_llm_extraction_uses_dotted_field_names(mocker):
    """Dotted field names (e.g. "CompanyAddress.City") must round-trip correctly.

    The mangled Pydantic attribute name (CompanyAddress_City) should map back to the
    dotted name in the extraction output - both as the field_confidence_scores
    key and the fields dict key, and fieldType must resolve from the schema
    rather than silently defaulting to "string".
    """
    import json

    from documentai_api.utils.schemas import DocumentSchema, SchemaField

    schema = DocumentSchema(
        document_type="payslip",
        description="Payslip",
        fields=[SchemaField(name="CompanyAddress.City", type="address", description="City")],
    )

    mock_response = MagicMock()
    mock_response.CompanyAddress_City = _make_field_response("Hartford", "Hartford")

    mock_completion = MagicMock()
    mock_completion.usage.input_tokens = 100
    mock_completion.usage.output_tokens = 50

    mocker.patch(
        "documentai_api.utils.ssm.get_llm_extractor_model_id",
        return_value="us.amazon.nova-pro-v1:0",
    )
    mocker.patch("documentai_api.utils.schemas.get_document_schema", return_value=schema)

    mock_client = MagicMock()
    mock_client.chat.completions.create_with_completion.return_value = (
        mock_response,
        mock_completion,
    )
    mocker.patch("instructor.from_bedrock", return_value=mock_client)
    mocker.patch(
        "documentai_api.services.aws_client_factory.AWSClientFactory.get_bedrock_runtime_client",
        return_value=MagicMock(),
    )
    mocker.patch("documentai_api.extractors.llm._write_llm_telemetry")

    result = run_llm_extraction(
        ddb_key="doc.json",
        document_type="payslip",
        ocr_blocks=OCR_BLOCKS,
    )

    assert result.field_confidence_scores == [{"CompanyAddress.City": pytest.approx(0.0)}]
    assert result.body is not None
    fields = json.loads(result.body)["fields"]
    assert "CompanyAddress.City" in fields
    assert "CompanyAddress_City" not in fields
    assert fields["CompanyAddress.City"]["fieldType"] == "address"


def test_run_llm_extraction_raises_on_missing_schema(mocker):
    mocker.patch(
        "documentai_api.utils.ssm.get_llm_extractor_model_id",
        return_value="us.amazon.nova-pro-v1:0",
    )
    mocker.patch("documentai_api.utils.schemas.get_document_schema", return_value=None)
    mocker.patch(
        "documentai_api.services.aws_client_factory.AWSClientFactory.get_bedrock_runtime_client",
        return_value=MagicMock(),
    )
    mocker.patch("instructor.from_bedrock", return_value=MagicMock())

    with pytest.raises(ValueError, match="No schema found"):
        run_llm_extraction(
            ddb_key="doc.json",
            document_type="unknown-type",
            ocr_blocks=OCR_BLOCKS,
        )


def test_run_llm_extraction_raises_on_empty_ocr(mocker):
    from documentai_api.utils.schemas import DocumentSchema, SchemaField

    schema = DocumentSchema(
        document_type="payslip",
        description="Payslip",
        fields=[SchemaField(name="employee_name", type="string", description="")],
    )
    mocker.patch(
        "documentai_api.utils.ssm.get_llm_extractor_model_id",
        return_value="us.amazon.nova-pro-v1:0",
    )
    mocker.patch("documentai_api.utils.schemas.get_document_schema", return_value=schema)
    mocker.patch(
        "documentai_api.services.aws_client_factory.AWSClientFactory.get_bedrock_runtime_client",
        return_value=MagicMock(),
    )
    mocker.patch("instructor.from_bedrock", return_value=MagicMock())

    with pytest.raises(ValueError, match="No OCR text available"):
        run_llm_extraction(
            ddb_key="doc.json",
            document_type="payslip",
            ocr_blocks=[],
        )
