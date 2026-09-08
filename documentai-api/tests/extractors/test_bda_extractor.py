import pytest

from documentai_api.extractors.bda import extract_bda_result


@pytest.mark.parametrize(
    ("bda_result", "expected_name", "expected_confidence"),
    [
        (
            {"matched_blueprint": {"name": "invoice_blueprint", "confidence": "0.95"}},
            "invoice_blueprint",
            "0.95",
        ),
        ({}, None, None),
    ],
)
def test_extract_bda_result_matched_blueprint(bda_result, expected_name, expected_confidence):
    _, matched_blueprint = extract_bda_result(bda_result, "s3://bucket/key")

    assert matched_blueprint.name == expected_name
    assert matched_blueprint.confidence == expected_confidence
