from documentai_api.cli.extraction_compare._types import _ResultData
from documentai_api.cli.extraction_compare.comparison import (
    _method_key,
    regen_comparison_md,
    write_comparison_md,
)
from documentai_api.constants.processing import ExtractMethod
from documentai_api.models.extraction_compare import CompareFieldResult, CompareResponse


def test_method_key_names_the_ocr_mapping_path_llm():
    assert _method_key(ExtractMethod.OCR_MAPPING) == _ResultData.LLM


def test_method_key_leaves_primary_methods_unchanged():
    assert _method_key(ExtractMethod.BDA) == ExtractMethod.BDA
    assert _method_key(ExtractMethod.TEXTRACT) == ExtractMethod.TEXTRACT


def _compare_response() -> CompareResponse:
    return CompareResponse(
        job_id="job-1",
        primary_method=ExtractMethod.BDA,
        is_completed=True,
        primary={"name": CompareFieldResult(value="a", confidence=0.9)},
        ocr_mapping={"name": CompareFieldResult(value="a", confidence=0.9)},
        cost={"us.amazon.nova-pro-v1:0": 0.0137872, "bda": 0.04},
        tokens={"us.amazon.nova-pro-v1:0": {"inputTokens": 14906, "outputTokens": 582}},
        pages=2,
    )


def test_regenerated_markdown_matches_the_live_run_cost_details(tmp_path):
    expected_dir = tmp_path / "expected"
    expected_dir.mkdir()

    write_comparison_md(
        "doc.pdf",
        _compare_response(),
        expected=None,
        expected_geo=None,
        md_dir=tmp_path / "md",
        data_dir=tmp_path / "data",
    )
    live = (tmp_path / "md" / "doc.md").read_text()
    (tmp_path / "md" / "doc.md").unlink()

    regen_comparison_md(tmp_path, expected_dir)

    regenerated = (tmp_path / "md" / "doc.md").read_text()
    assert "(14906 in / 582 out)" in regenerated
    assert "bda: $0.04000000 (2 page(s))" in regenerated
    assert regenerated == live
