"""Tests for preclassification utilities.

Unit tests run always. Integration tests (marked @pytest.mark.integration) call
real Bedrock and require AWS credentials:

    uv run pytest tests/utils/test_preclassification.py -m integration
"""

import json
from pathlib import Path

import pytest

from documentai_api.config.constants import ConfigDefaults, PreclassificationCategory
from documentai_api.utils.preclassification import (
    _build_blueprint_prompt,
    find_matching_blueprint,
    preclassify_document,
)

SAMPLE_IMAGE = b"\x89PNG\r\n" + b"\x00" * 100


def _mock_invoke_response(parsed: dict) -> dict:
    return {
        "output": {"message": {"content": [{"text": json.dumps(parsed)}]}},
        "usage": {"inputTokens": 100, "outputTokens": 50},
    }


def _patch_invoke(monkeypatch, response):
    monkeypatch.setattr(
        "documentai_api.utils.preclassification.invoke_model", lambda **kwargs: response
    )
    monkeypatch.setattr(
        "documentai_api.utils.preclassification._get_classification_prompt", lambda: "test prompt"
    )


# =============================================================================
# Unit tests
# =============================================================================


def test_classifies_image_successfully(monkeypatch):
    response = _mock_invoke_response(
        {
            "document_type": "tax_documents",
            "confidence": 0.95,
            "document_count": 1,
        }
    )
    _patch_invoke(monkeypatch, response)

    result = preclassify_document(SAMPLE_IMAGE, "image/png")

    assert result.document_type == "tax_documents"
    assert result.confidence == 0.95
    assert result.document_count == 1


def test_skips_unsupported_content_type():
    result = preclassify_document(SAMPLE_IMAGE, "text/plain")

    assert result.document_type == "other_document"
    assert result.confidence == 0.0
    assert result.document_count == 1


def test_skips_oversized_image():
    large_image = b"\x00" * (int(ConfigDefaults.BDA_MAX_IMAGE_SIZE_BYTES) + 1)

    result = preclassify_document(large_image, "image/jpeg")

    assert result.document_type == "other_document"
    assert result.confidence == 0.0


def test_pdf_not_subject_to_image_size_limit(monkeypatch):
    """PDFs bypass the image size check - BDA handles large PDFs natively."""
    large_pdf = b"%PDF-1.4" + b"\x00" * (int(ConfigDefaults.BDA_MAX_IMAGE_SIZE_BYTES) + 1)
    response = _mock_invoke_response(
        {
            "document_type": "tax_documents",
            "confidence": 0.9,
            "document_count": 1,
        }
    )
    _patch_invoke(monkeypatch, response)

    result = preclassify_document(large_pdf, "application/pdf")

    assert result.document_type == "tax_documents"


@pytest.mark.parametrize("category", [c.value for c in PreclassificationCategory])
def test_all_enum_values_accepted(monkeypatch, category):
    """Every PreclassificationCategory value is accepted without fallback."""
    response = _mock_invoke_response(
        {
            "document_type": category,
            "confidence": 0.9,
            "document_count": 1,
        }
    )
    _patch_invoke(monkeypatch, response)

    result = preclassify_document(SAMPLE_IMAGE, "image/png")

    assert result.document_type == category


def test_invalid_document_type_falls_back(monkeypatch):
    response = _mock_invoke_response(
        {
            "document_type": "invented_category",
            "confidence": 0.8,
            "document_count": 1,
        }
    )
    _patch_invoke(monkeypatch, response)

    result = preclassify_document(SAMPLE_IMAGE, "image/png")

    assert result.document_type == "other_document"


def test_other_document_is_valid_type(monkeypatch):
    response = _mock_invoke_response(
        {
            "document_type": "other_document",
            "confidence": 0.6,
            "document_count": 1,
        }
    )
    _patch_invoke(monkeypatch, response)

    result = preclassify_document(SAMPLE_IMAGE, "image/png")

    assert result.document_type == "other_document"
    assert result.confidence == 0.6


def test_unrecognized_type_falls_back_to_other_document(monkeypatch):
    response = _mock_invoke_response(
        {
            "document_type": "system_reject",
            "confidence": 0.9,
            "document_count": 0,
        }
    )
    _patch_invoke(monkeypatch, response)

    result = preclassify_document(SAMPLE_IMAGE, "image/png")

    assert result.document_type == "other_document"


def test_invocation_failure_returns_default(monkeypatch):
    monkeypatch.setattr(
        "documentai_api.utils.preclassification.invoke_model",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("Bedrock timeout")),
    )
    monkeypatch.setattr(
        "documentai_api.utils.preclassification._get_classification_prompt", lambda: "test prompt"
    )

    result = preclassify_document(SAMPLE_IMAGE, "image/png")

    assert result.document_type == "other_document"
    assert result.confidence == 0.0


def test_invalid_json_response_returns_default(monkeypatch):
    monkeypatch.setattr(
        "documentai_api.utils.preclassification.invoke_model",
        lambda **kwargs: {"content": [{"text": "not valid json"}]},
    )
    monkeypatch.setattr(
        "documentai_api.utils.preclassification._get_classification_prompt", lambda: "test prompt"
    )

    result = preclassify_document(SAMPLE_IMAGE, "image/png")

    assert result.document_type == "other_document"
    assert result.confidence == 0.0


def test_non_object_json_response_returns_default(monkeypatch):
    """A well-formed but non-object JSON output (e.g. a list) fails schema validation."""
    monkeypatch.setattr(
        "documentai_api.utils.preclassification.invoke_model",
        lambda **kwargs: {
            "output": {"message": {"content": [{"text": '["tax_documents", 0.9]'}]}},
            "usage": {"inputTokens": 1, "outputTokens": 1},
        },
    )
    monkeypatch.setattr(
        "documentai_api.utils.preclassification._get_classification_prompt", lambda: "test prompt"
    )

    result = preclassify_document(SAMPLE_IMAGE, "image/png")

    assert result.document_type == "other_document"
    assert result.confidence == 0.0


def test_parse_defaults_when_fields_missing(monkeypatch):
    """Pydantic defaults fill in when model omits fields."""
    response = _mock_invoke_response({"document_type": "tax_documents"})
    _patch_invoke(monkeypatch, response)

    result = preclassify_document(SAMPLE_IMAGE, "image/png")

    assert result.document_type == "tax_documents"
    assert result.confidence == 0.0
    assert result.document_count == 1


def test_empty_document_bytes(monkeypatch):
    """Empty bytes still go through - model will return an unrecognized type."""
    response = _mock_invoke_response(
        {
            "document_type": "system_reject",
            "confidence": 0.9,
            "document_count": 0,
        }
    )
    _patch_invoke(monkeypatch, response)

    result = preclassify_document(b"", "image/png")

    assert result.document_type == "other_document"


def test_prompt_includes_all_categories():
    from documentai_api.config.constants import PreClassificationDefaults

    prompt = PreClassificationDefaults.PROMPT
    for category in PreclassificationCategory:
        assert category.value in prompt, f"{category.value} missing from prompt"


@pytest.mark.parametrize(
    ("content_type", "expected_format"),
    [
        ("image/jpeg", "jpeg"),
        ("image/png", "png"),
        ("image/gif", "gif"),
        ("image/webp", "webp"),
    ],
)
def test_image_content_type_format_extraction(monkeypatch, content_type, expected_format):
    captured = {}

    def capture_invoke(**kwargs):
        captured["messages"] = kwargs["messages"]
        return _mock_invoke_response(
            {
                "document_type": "tax_documents",
                "confidence": 0.9,
                "document_count": 1,
            }
        )

    monkeypatch.setattr("documentai_api.utils.preclassification.invoke_model", capture_invoke)
    monkeypatch.setattr(
        "documentai_api.utils.preclassification._get_classification_prompt", lambda: "test prompt"
    )

    preclassify_document(SAMPLE_IMAGE, content_type)

    assert captured["messages"][0]["content"][0]["image"]["format"] == expected_format


def test_pdf_uses_document_block(monkeypatch):
    captured = {}

    def capture_invoke(**kwargs):
        captured["messages"] = kwargs["messages"]
        return _mock_invoke_response(
            {
                "document_type": "tax_documents",
                "confidence": 0.9,
                "document_count": 1,
            }
        )

    monkeypatch.setattr("documentai_api.utils.preclassification.invoke_model", capture_invoke)
    monkeypatch.setattr(
        "documentai_api.utils.preclassification._get_classification_prompt", lambda: "test prompt"
    )

    pdf_bytes = b"%PDF-1.4 fake"
    preclassify_document(pdf_bytes, "application/pdf")

    doc_block = captured["messages"][0]["content"][0]
    assert doc_block["document"]["format"] == "pdf"
    assert doc_block["document"]["name"] == "document"
    assert doc_block["document"]["source"]["bytes"] == pdf_bytes


def test_message_structure(monkeypatch):
    """Verify message has user role, content block first, prompt second."""
    captured = {}

    def capture_invoke(**kwargs):
        captured["messages"] = kwargs["messages"]
        captured["max_tokens"] = kwargs.get("max_tokens")
        return _mock_invoke_response(
            {
                "document_type": "tax_documents",
                "confidence": 0.9,
                "document_count": 1,
            }
        )

    monkeypatch.setattr("documentai_api.utils.preclassification.invoke_model", capture_invoke)
    monkeypatch.setattr(
        "documentai_api.utils.preclassification._get_classification_prompt", lambda: "test prompt"
    )

    preclassify_document(SAMPLE_IMAGE, "image/png")

    msg = captured["messages"][0]
    assert msg["role"] == "user"
    assert len(msg["content"]) == 2
    assert "image" in msg["content"][0] or "document" in msg["content"][0]
    assert "text" in msg["content"][1]


def test_confidence_clamped_to_0_1(monkeypatch):
    """Out-of-range confidence values are clamped."""
    response = _mock_invoke_response(
        {
            "document_type": "tax_documents",
            "confidence": 1.5,
            "document_count": 1,
        }
    )
    _patch_invoke(monkeypatch, response)
    result = preclassify_document(SAMPLE_IMAGE, "image/png")
    assert result.confidence == 1.0

    response = _mock_invoke_response(
        {
            "document_type": "tax_documents",
            "confidence": -0.5,
            "document_count": 1,
        }
    )
    _patch_invoke(monkeypatch, response)
    result = preclassify_document(SAMPLE_IMAGE, "image/png")
    assert result.confidence == 0.0


def test_document_count_clamped_to_non_negative(monkeypatch):
    """Negative document_count is clamped to 0."""
    response = _mock_invoke_response(
        {
            "document_type": "tax_documents",
            "confidence": 0.9,
            "document_count": -1,
        }
    )
    _patch_invoke(monkeypatch, response)
    result = preclassify_document(SAMPLE_IMAGE, "image/png")
    assert result.document_count == 0


def test_get_classification_prompt_uses_default(monkeypatch):
    """When no SSM param configured, returns the hardcoded default prompt."""
    from documentai_api.config.constants import PreClassificationDefaults
    from documentai_api.utils.preclassification import _get_classification_prompt

    monkeypatch.setattr(
        "documentai_api.utils.preclassification.get_aws_config",
        lambda: type("C", (), {"bedrock_classification_prompt_param": None})(),
    )

    result = _get_classification_prompt()
    assert result == PreClassificationDefaults.PROMPT


def test_get_classification_prompt_reads_ssm(monkeypatch):
    """When SSM param is configured, reads from SSM."""
    from documentai_api.utils.preclassification import _get_classification_prompt

    custom_prompt = "Custom classification prompt"
    monkeypatch.setattr(
        "documentai_api.utils.preclassification.get_aws_config",
        lambda: type("C", (), {"bedrock_classification_prompt_param": "/test/prompt"})(),
    )
    monkeypatch.setattr(
        "documentai_api.utils.preclassification.get_parameter_value",
        lambda name, default=None: custom_prompt,
    )

    result = _get_classification_prompt()
    assert result == custom_prompt


def test_get_model_id_uses_default(monkeypatch):
    """When no SSM param configured, returns the default model ID."""
    from documentai_api.config.constants import PreClassificationDefaults
    from documentai_api.utils.preclassification import _get_model_id

    monkeypatch.setattr(
        "documentai_api.utils.preclassification.get_aws_config",
        lambda: type("C", (), {"bedrock_classification_model_id_param": None})(),
    )

    result = _get_model_id()
    assert result == PreClassificationDefaults.MODEL_ID


def test_get_model_id_reads_ssm(monkeypatch):
    """When SSM param is configured, reads model ID from SSM."""
    from documentai_api.utils.preclassification import _get_model_id

    monkeypatch.setattr(
        "documentai_api.utils.preclassification.get_aws_config",
        lambda: type("C", (), {"bedrock_classification_model_id_param": "/test/model"})(),
    )
    monkeypatch.setattr(
        "documentai_api.utils.preclassification.get_parameter_value",
        lambda name, default=None: "us.amazon.nova-pro-v1:0",
    )

    result = _get_model_id()
    assert result == "us.amazon.nova-pro-v1:0"


def test_invoke_uses_max_tokens(monkeypatch):
    """Verify invoke_model is called with max_tokens=256."""
    captured = {}

    def mock_invoke_model(model_id, messages, max_tokens=256, temperature=None):
        captured["max_tokens"] = max_tokens
        captured["model_id"] = model_id
        captured["temperature"] = temperature
        return {
            "content": [
                {
                    "text": '{"document_type": "tax_documents", "confidence": 0.9, "document_count": 1}'
                }
            ]
        }

    monkeypatch.setattr("documentai_api.utils.preclassification.invoke_model", mock_invoke_model)
    monkeypatch.setattr(
        "documentai_api.utils.preclassification._get_classification_prompt", lambda: "test prompt"
    )
    monkeypatch.setattr(
        "documentai_api.utils.preclassification._get_model_id", lambda: "test-model"
    )

    preclassify_document(SAMPLE_IMAGE, "image/png")

    assert captured["max_tokens"] == 256
    assert captured["model_id"] == "test-model"


# =============================================================================
# find_matching_blueprint unit tests
# =============================================================================


SAMPLE_SCHEMAS = {
    "W2": {
        "documentType": "W2",
        "description": "IRS W-2 Wage and Tax Statement",
        "category": "tax_documents",
        "fields": [{"name": "employer_ein", "type": "string"}, {"name": "wages", "type": "number"}],
    },
    "paystub": {
        "documentType": "paystub",
        "description": "Employee pay stub",
        "category": "employment_wages",
        "fields": [
            {"name": "employee_name", "type": "string"},
            {"name": "pay_period", "type": "string"},
        ],
    },
}


def test_build_blueprint_prompt_lists_all_types():
    prompt = _build_blueprint_prompt(SAMPLE_SCHEMAS)
    assert "W2" in prompt
    assert "paystub" in prompt
    assert "IRS W-2 Wage and Tax Statement" in prompt
    assert "Employee pay stub" in prompt
    assert "Fields: employer_ein, wages" in prompt
    assert "Fields: employee_name, pay_period" in prompt


def test_build_blueprint_prompt_handles_missing_description():
    schemas = {"receipt": {"documentType": "receipt", "fields": []}}
    prompt = _build_blueprint_prompt(schemas)
    assert "- receipt" in prompt


def test_find_matching_blueprint_returns_match(monkeypatch):
    response = _mock_invoke_response({"matched_blueprint": "W2", "confidence": 0.92})
    _patch_invoke(monkeypatch, response)
    monkeypatch.setattr("documentai_api.utils.schemas.get_all_schemas", lambda: SAMPLE_SCHEMAS)

    result = find_matching_blueprint(SAMPLE_IMAGE, "image/png")

    assert result.matched_document_type == "W2"
    assert result.confidence == 0.92
    assert result.input_tokens == 100
    assert result.output_tokens == 50
    assert result.duration_seconds is not None


def test_find_matching_blueprint_returns_none_when_no_match(monkeypatch):
    response = _mock_invoke_response({"matched_blueprint": None, "confidence": 0.0})
    _patch_invoke(monkeypatch, response)
    monkeypatch.setattr("documentai_api.utils.schemas.get_all_schemas", lambda: SAMPLE_SCHEMAS)

    result = find_matching_blueprint(SAMPLE_IMAGE, "image/png")

    assert result.matched_document_type is None
    assert result.confidence == 0.0


def test_find_matching_blueprint_rejects_unknown_type(monkeypatch):
    """Model returns a type not in schemas -> treated as no match."""
    response = _mock_invoke_response({"matched_blueprint": "invented_type", "confidence": 0.8})
    _patch_invoke(monkeypatch, response)
    monkeypatch.setattr("documentai_api.utils.schemas.get_all_schemas", lambda: SAMPLE_SCHEMAS)

    result = find_matching_blueprint(SAMPLE_IMAGE, "image/png")

    assert result.matched_document_type is None


def test_find_matching_blueprint_returns_none_when_no_schemas(monkeypatch):
    """No schemas available -> early return with no match."""
    monkeypatch.setattr("documentai_api.utils.schemas.get_all_schemas", lambda: {})

    result = find_matching_blueprint(SAMPLE_IMAGE, "image/png")

    assert result.matched_document_type is None
    assert result.confidence == 0.0


def test_find_matching_blueprint_handles_invocation_failure(monkeypatch):
    monkeypatch.setattr(
        "documentai_api.utils.preclassification.invoke_model",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("timeout")),
    )
    monkeypatch.setattr("documentai_api.utils.schemas.get_all_schemas", lambda: SAMPLE_SCHEMAS)

    result = find_matching_blueprint(SAMPLE_IMAGE, "image/png")

    assert result.matched_document_type is None
    assert result.confidence == 0.0


def test_find_matching_blueprint_handles_invalid_json(monkeypatch):
    bad_response = {
        "output": {"message": {"content": [{"text": "not json at all"}]}},
        "usage": {"inputTokens": 10, "outputTokens": 5},
    }
    _patch_invoke(monkeypatch, bad_response)
    monkeypatch.setattr("documentai_api.utils.schemas.get_all_schemas", lambda: SAMPLE_SCHEMAS)

    result = find_matching_blueprint(SAMPLE_IMAGE, "image/png")

    assert result.matched_document_type is None
    assert result.input_tokens == 10
    assert result.output_tokens == 5


def test_find_matching_blueprint_confidence_clamped(monkeypatch):
    response = _mock_invoke_response({"matched_blueprint": "W2", "confidence": 1.5})
    _patch_invoke(monkeypatch, response)
    monkeypatch.setattr("documentai_api.utils.schemas.get_all_schemas", lambda: SAMPLE_SCHEMAS)

    result = find_matching_blueprint(SAMPLE_IMAGE, "image/png")

    assert result.confidence == 1.0


def test_find_matching_blueprint_uses_pdf_document_block(monkeypatch):
    captured = {}

    def capture_invoke(**kwargs):
        captured["messages"] = kwargs["messages"]
        return _mock_invoke_response({"matched_blueprint": None, "confidence": 0.0})

    monkeypatch.setattr("documentai_api.utils.preclassification.invoke_model", capture_invoke)
    monkeypatch.setattr(
        "documentai_api.utils.preclassification._get_model_id", lambda: "test-model"
    )
    monkeypatch.setattr("documentai_api.utils.schemas.get_all_schemas", lambda: SAMPLE_SCHEMAS)

    find_matching_blueprint(b"%PDF-1.4 fake", "application/pdf")

    doc_block = captured["messages"][0]["content"][0]
    assert "document" in doc_block
    assert doc_block["document"]["format"] == "pdf"


# =============================================================================
# Integration tests - call real Bedrock API
# =============================================================================

FIXTURES_DIR = Path(__file__).parent.parent / "helpers" / "fixtures" / "test-documents"
EXPECTED_FILE = FIXTURES_DIR / "expected.json"

CONTENT_TYPE_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".pdf": "application/pdf",
}


def _load_expected():
    if not EXPECTED_FILE.exists():
        return {}
    with open(EXPECTED_FILE) as f:
        return json.load(f)


def _get_content_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return CONTENT_TYPE_MAP.get(ext, "application/octet-stream")


_expected_items = [(k, v["preclassificationCategory"]) for k, v in _load_expected().items()]


@pytest.mark.integration
@pytest.mark.parametrize(
    ("filename", "expected_category"),
    _expected_items
    or [pytest.param("skip", "skip", marks=pytest.mark.skip(reason="No test fixtures"))],
)
def test_preclassify_real_document(filename, expected_category, monkeypatch, real_aws_credentials):
    """Classify a real document and assert it routes to the correct category."""
    monkeypatch.setattr(
        "documentai_api.utils.preclassification._get_model_id",
        lambda: "us.amazon.nova-lite-v1:0",
    )

    filepath = FIXTURES_DIR / filename
    if not filepath.exists():
        pytest.skip(f"Test fixture not found: {filepath}")

    document_bytes = filepath.read_bytes()
    content_type = _get_content_type(filename)

    result = preclassify_document(document_bytes, content_type)

    assert result.document_type == expected_category, (
        f"{filename}: expected {expected_category}, got {result.document_type} "
        f"(confidence={result.confidence})"
    )
    assert result.confidence >= 0.5, f"{filename}: confidence too low: {result.confidence}"
    assert result.document_count >= 1


# =============================================================================
# find_matching_blueprint integration tests
# =============================================================================

_BLUEPRINT_MATCH_EXPECTATIONS = [
    ("synthetic-tax-w2-wage-statement.png", "W2", "tax_documents"),
    (
        "synthetic-public-benefits-income-proof-pay-statement-rendered.png",
        "Payslip",
        "employment_wages",
    ),
    (
        "synthetic-snap-income-proof-employment-wage-verification-letter-rendered.png",
        "Employment-Verification-Letter",
        "employment_wages",
    ),
    (
        "synthetic-drivers-license-desk-background.jpg",
        "US-drivers-licenses",
        "identity_verification",
    ),
    ("synthetic-wic-adjunctive-eligibility-snap-benefits-letter.jpg", None, "government_benefits"),
    (
        "synthetic-wic-certification-pregnancy-verification-clinic-note.jpg",
        None,
        "government_benefits",
    ),
]


@pytest.fixture
def bda_env(reset_env, monkeypatch):
    """Restore BDA env vars needed for integration tests that call get_all_schemas()."""
    arn = reset_env.get("BDA_PROJECT_ARN_ALL")
    if not arn:
        pytest.skip("BDA_PROJECT_ARN_ALL not set in environment")
    monkeypatch.setenv("BDA_PROJECT_ARN_ALL", arn)
    if "BDA_REGION" in reset_env:
        monkeypatch.setenv("BDA_REGION", reset_env["BDA_REGION"])


@pytest.mark.integration
def test_get_all_schemas_has_descriptions(real_aws_credentials, bda_env):
    """Verify get_all_schemas() returns schemas with non-empty descriptions."""
    from documentai_api.utils.schemas import get_all_schemas, invalidate_schema_cache

    invalidate_schema_cache()
    schemas = get_all_schemas()

    assert len(schemas) > 0, "No schemas returned from BDA"

    missing_descriptions = [
        doc_type for doc_type, schema in schemas.items() if not schema.get("description")
    ]
    assert not missing_descriptions, (
        f"Schemas missing descriptions: {missing_descriptions}. "
        "Blueprint matching prompt needs descriptions to work."
    )

    missing_categories = [
        doc_type for doc_type, schema in schemas.items() if not schema.get("category")
    ]
    assert not missing_categories, f"Schemas missing category: {missing_categories}"

    print(f"\nSchemas fetched: {len(schemas)} types, all with descriptions")
    for doc_type, schema in schemas.items():
        print(f"  {doc_type}: {schema.get('description', '')[:60]}...")


@pytest.mark.integration
@pytest.mark.parametrize(
    ("filename", "expected_match", "category"),
    _BLUEPRINT_MATCH_EXPECTATIONS,
)
def test_find_matching_blueprint_real(
    filename, expected_match, category, monkeypatch, real_aws_credentials, bda_env
):
    """Match a real document against real BDA schemas via Bedrock."""
    from documentai_api.utils.schemas import invalidate_schema_cache

    monkeypatch.setattr(
        "documentai_api.utils.preclassification._get_model_id",
        lambda: "us.amazon.nova-lite-v1:0",
    )

    invalidate_schema_cache()

    filepath = FIXTURES_DIR / filename
    if not filepath.exists():
        pytest.skip(f"Test fixture not found: {filepath}")

    document_bytes = filepath.read_bytes()
    content_type = _get_content_type(filename)

    result = find_matching_blueprint(document_bytes, content_type, category=category)

    if expected_match is None:
        assert result.matched_document_type is None, (
            f"{filename}: expected no match, got '{result.matched_document_type}' "
            f"(confidence={result.confidence})"
        )
    else:
        assert result.matched_document_type == expected_match, (
            f"{filename}: expected '{expected_match}', got '{result.matched_document_type}' "
            f"(confidence={result.confidence})"
        )
        assert result.confidence >= 0.5, f"{filename}: confidence too low: {result.confidence}"

    assert result.input_tokens is not None
    assert result.input_tokens > 0
    assert result.output_tokens is not None
    assert result.output_tokens > 0
    assert result.duration_seconds is not None
    assert result.duration_seconds > 0

    print(
        f"\n{filename}: matched={result.matched_document_type}, confidence={result.confidence}, "
        f"tokens={result.input_tokens}/{result.output_tokens}, duration={result.duration_seconds}s"
    )
