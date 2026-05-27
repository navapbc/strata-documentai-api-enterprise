"""Tests for preclassify_document in utils/bedrock.py.

Unit tests run always. Integration tests (marked @pytest.mark.integration) call
real Bedrock and require AWS credentials:

    uv run pytest tests/utils/test_bedrock_preclassification.py -m integration
"""

import json
import os
from pathlib import Path

import pytest

from documentai_api.config.constants import ConfigDefaults, PreclassificationCategory
from documentai_api.utils.bedrock import preclassify_document

SAMPLE_IMAGE = b"\x89PNG\r\n" + b"\x00" * 100


def _mock_invoke_response(parsed: dict) -> dict:
    return {"content": [{"text": json.dumps(parsed)}]}


def _patch_invoke(monkeypatch, response):
    monkeypatch.setattr("documentai_api.utils.bedrock._invoke", lambda **kwargs: response)
    monkeypatch.setattr(
        "documentai_api.utils.bedrock._get_classification_prompt", lambda: "test prompt"
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
            "is_document": True,
            "is_blurry": False,
        }
    )
    _patch_invoke(monkeypatch, response)

    result = preclassify_document(SAMPLE_IMAGE, "image/png")

    assert result.document_type == "tax_documents"
    assert result.confidence == 0.95
    assert result.document_count == 1
    assert result.is_document is True
    assert result.is_blurry is False


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
            "is_document": True,
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
            "is_document": True,
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
            "is_document": True,
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
            "is_document": True,
        }
    )
    _patch_invoke(monkeypatch, response)

    result = preclassify_document(SAMPLE_IMAGE, "image/png")

    assert result.document_type == "other_document"
    assert result.confidence == 0.6


def test_system_reject_is_valid_type(monkeypatch):
    response = _mock_invoke_response(
        {
            "document_type": "system_reject",
            "confidence": 0.9,
            "document_count": 0,
            "is_document": False,
        }
    )
    _patch_invoke(monkeypatch, response)

    result = preclassify_document(SAMPLE_IMAGE, "image/png")

    assert result.document_type == "system_reject"
    assert result.is_document is False


def test_invocation_failure_returns_default(monkeypatch):
    monkeypatch.setattr(
        "documentai_api.utils.bedrock._invoke",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("Bedrock timeout")),
    )
    monkeypatch.setattr(
        "documentai_api.utils.bedrock._get_classification_prompt", lambda: "test prompt"
    )

    result = preclassify_document(SAMPLE_IMAGE, "image/png")

    assert result.document_type == "other_document"
    assert result.confidence == 0.0


def test_invalid_json_response_returns_default(monkeypatch):
    monkeypatch.setattr(
        "documentai_api.utils.bedrock._invoke",
        lambda **kwargs: {"content": [{"text": "not valid json"}]},
    )
    monkeypatch.setattr(
        "documentai_api.utils.bedrock._get_classification_prompt", lambda: "test prompt"
    )

    result = preclassify_document(SAMPLE_IMAGE, "image/png")

    assert result.document_type == "other_document"
    assert result.confidence == 0.0


def test_parse_defaults_when_fields_missing(monkeypatch):
    """bedrock.py .get() calls supply defaults when model omits fields."""
    response = _mock_invoke_response({"document_type": "tax_documents"})
    _patch_invoke(monkeypatch, response)

    result = preclassify_document(SAMPLE_IMAGE, "image/png")

    assert result.document_type == "tax_documents"
    assert result.confidence == 0.0
    assert result.document_count == 1
    assert result.is_document is True
    assert result.is_blurry is False


def test_blurry_detection(monkeypatch):
    response = _mock_invoke_response(
        {
            "document_type": "tax_documents",
            "confidence": 0.3,
            "document_count": 1,
            "is_document": True,
            "is_blurry": True,
        }
    )
    _patch_invoke(monkeypatch, response)

    result = preclassify_document(SAMPLE_IMAGE, "image/png")

    assert result.is_blurry is True
    assert result.confidence == 0.3


def test_empty_document_bytes(monkeypatch):
    """Empty bytes still go through - model will likely return system_reject."""
    response = _mock_invoke_response(
        {
            "document_type": "system_reject",
            "confidence": 0.9,
            "document_count": 0,
            "is_document": False,
        }
    )
    _patch_invoke(monkeypatch, response)

    result = preclassify_document(b"", "image/png")

    assert result.document_type == "system_reject"


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
                "is_document": True,
            }
        )

    monkeypatch.setattr("documentai_api.utils.bedrock._invoke", capture_invoke)
    monkeypatch.setattr(
        "documentai_api.utils.bedrock._get_classification_prompt", lambda: "test prompt"
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
                "is_document": True,
            }
        )

    monkeypatch.setattr("documentai_api.utils.bedrock._invoke", capture_invoke)
    monkeypatch.setattr(
        "documentai_api.utils.bedrock._get_classification_prompt", lambda: "test prompt"
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
                "is_document": True,
            }
        )

    monkeypatch.setattr("documentai_api.utils.bedrock._invoke", capture_invoke)
    monkeypatch.setattr(
        "documentai_api.utils.bedrock._get_classification_prompt", lambda: "test prompt"
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
            "is_document": True,
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
            "is_document": True,
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
            "is_document": True,
        }
    )
    _patch_invoke(monkeypatch, response)
    result = preclassify_document(SAMPLE_IMAGE, "image/png")
    assert result.document_count == 0


def test_get_classification_prompt_uses_default(monkeypatch):
    """When no SSM param configured, returns the hardcoded default prompt."""
    from documentai_api.config.constants import PreClassificationDefaults
    from documentai_api.utils.bedrock import _get_classification_prompt

    monkeypatch.setattr(
        "documentai_api.utils.bedrock.get_aws_config",
        lambda: type("C", (), {"bedrock_classification_prompt_param": None})(),
    )

    result = _get_classification_prompt()
    assert result == PreClassificationDefaults.PROMPT


def test_get_classification_prompt_reads_ssm(monkeypatch):
    """When SSM param is configured, reads from SSM."""
    from documentai_api.utils.bedrock import _get_classification_prompt

    custom_prompt = "Custom classification prompt"
    monkeypatch.setattr(
        "documentai_api.utils.bedrock.get_aws_config",
        lambda: type("C", (), {"bedrock_classification_prompt_param": "/test/prompt"})(),
    )
    monkeypatch.setattr(
        "documentai_api.utils.bedrock.get_parameter_value", lambda name, default=None: custom_prompt
    )

    result = _get_classification_prompt()
    assert result == custom_prompt


def test_get_model_id_uses_default(monkeypatch):
    """When no SSM param configured, returns the default model ID."""
    from documentai_api.config.constants import PreClassificationDefaults
    from documentai_api.utils.bedrock import _get_model_id

    monkeypatch.setattr(
        "documentai_api.utils.bedrock.get_aws_config",
        lambda: type("C", (), {"bedrock_classification_model_id_param": None})(),
    )

    result = _get_model_id()
    assert result == PreClassificationDefaults.MODEL_ID


def test_get_model_id_reads_ssm(monkeypatch):
    """When SSM param is configured, reads model ID from SSM."""
    from documentai_api.utils.bedrock import _get_model_id

    monkeypatch.setattr(
        "documentai_api.utils.bedrock.get_aws_config",
        lambda: type("C", (), {"bedrock_classification_model_id_param": "/test/model"})(),
    )
    monkeypatch.setattr(
        "documentai_api.utils.bedrock.get_parameter_value",
        lambda name, default=None: "us.amazon.nova-pro-v1:0",
    )

    result = _get_model_id()
    assert result == "us.amazon.nova-pro-v1:0"


def test_invoke_uses_max_tokens(monkeypatch):
    """Verify invoke_model is called with max_tokens=256."""
    captured = {}

    def mock_invoke_model(model_id, messages, max_tokens=256):
        captured["max_tokens"] = max_tokens
        captured["model_id"] = model_id
        return {
            "content": [
                {
                    "text": '{"document_type": "tax_documents", "confidence": 0.9, "document_count": 1, "is_document": true}'
                }
            ]
        }

    monkeypatch.setattr("documentai_api.utils.bedrock.invoke_model", mock_invoke_model)
    monkeypatch.setattr(
        "documentai_api.utils.bedrock._get_classification_prompt", lambda: "test prompt"
    )
    monkeypatch.setattr("documentai_api.utils.bedrock._get_model_id", lambda: "test-model")

    preclassify_document(SAMPLE_IMAGE, "image/png")

    assert captured["max_tokens"] == 256
    assert captured["model_id"] == "test-model"


def test_string_false_coerced_correctly(monkeypatch):
    """String 'false' from model correctly becomes False."""
    response = _mock_invoke_response(
        {
            "document_type": "tax_documents",
            "confidence": 0.9,
            "document_count": 1,
            "is_document": "true",
            "is_blurry": "false",
        }
    )
    _patch_invoke(monkeypatch, response)
    result = preclassify_document(SAMPLE_IMAGE, "image/png")
    assert result.is_document is True
    assert result.is_blurry is False


def test_native_bools_pass_through(monkeypatch):
    """Native bool values from model work correctly."""
    response = _mock_invoke_response(
        {
            "document_type": "tax_documents",
            "confidence": 0.9,
            "document_count": 1,
            "is_document": True,
            "is_blurry": True,
        }
    )
    _patch_invoke(monkeypatch, response)
    result = preclassify_document(SAMPLE_IMAGE, "image/png")
    assert result.is_document is True
    assert result.is_blurry is True


# =============================================================================
# Integration tests - call real Bedrock API
# =============================================================================

FIXTURES_DIR = Path(__file__).parent.parent / "helpers" / "fixtures" / "test-documents"
EXPECTED_FILE = FIXTURES_DIR / "expected_classifications.json"

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


_expected_items = _load_expected().items()


@pytest.fixture
def restore_aws_env(reset_env):
    """Restore AWS credentials cleared by the session-scoped reset_env fixture."""
    for key in (
        "HOME",
        "AWS_PROFILE",
        "AWS_DEFAULT_REGION",
        "AWS_REGION",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
    ):
        if key in reset_env:
            os.environ[key] = reset_env[key]


@pytest.mark.integration
@pytest.mark.parametrize(
    ("filename", "expected_category"),
    _expected_items
    or [pytest.param("skip", "skip", marks=pytest.mark.skip(reason="No test fixtures"))],
)
def test_preclassify_real_document(filename, expected_category, monkeypatch, restore_aws_env):
    """Classify a real document and assert it routes to the correct category."""
    monkeypatch.setattr(
        "documentai_api.utils.bedrock._get_model_id",
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
    # 0.5 threshold: below this the model is essentially guessing.
    # If model accuracy drifts, adjust threshold or retune prompt.
    assert result.confidence >= 0.5, f"{filename}: confidence too low: {result.confidence}"
    assert result.is_document is True
    assert result.document_count >= 1
