import pytest

from documentai_api.utils import bda as bda_util


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
    assert bda_util.extract_region_from_bda_arn(arn) == expected_region


def test_get_text_from_standard_blueprint_document_modality():
    bda_result = {
        "metadata": {"semantic_modality": "DOCUMENT"},
        "pages": [{"representation": {"text": "  Sample document text  "}}],
    }
    text = bda_util.get_text_from_standard_blueprint(bda_result)
    assert text == "Sample document text"


def test_get_text_from_standard_blueprint_image_modality():
    bda_result = {
        "metadata": {"semantic_modality": "IMAGE"},
        "image": {
            "text_words": [
                {"text": "Hello"},
                {"text": "World"},
                {"text": ""},
            ]
        },
    }
    text = bda_util.get_text_from_standard_blueprint(bda_result)
    assert text == "Hello World"


def test_extract_field_values_from_bda_results():
    bda_result = {
        "explainability_info": [
            {
                "name": {"confidence": 0.95, "value": "John"},
                "email": {"confidence": 0.85, "value": "john@example.com"},
            }
        ]
    }
    metadata, field_values = bda_util.extract_field_values_from_bda_results(bda_result)

    assert len(metadata.confidence_scores) == 2
    assert len(metadata.empty_fields) == 0
    assert field_values["name"] == "John"
    assert field_values["email"] == "john@example.com"

    # confirm extract_field_metadata_from_bda_results wrapper returns same metadata
    metadata_only = bda_util.extract_field_metadata_from_bda_results(bda_result)
    assert metadata_only.confidence_scores == metadata.confidence_scores
    assert metadata_only.empty_fields == metadata.empty_fields
