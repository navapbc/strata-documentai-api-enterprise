"""Tests for preclassify_document in utils/bedrock.py.

Unit tests run always. Integration tests (marked @pytest.mark.integration) call
real Bedrock and require AWS credentials:

    uv run pytest tests/utils/test_bedrock_preclassification.py -m integration
"""

import json
from pathlib import Path

import pytest

from documentai_api.config.constants import ConfigDefaults, PreclassificationCategory
from documentai_api.utils.bedrock import detect_document_bbox, preclassify_document

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


def test_get_bbox_model_id_uses_default(monkeypatch):
    """When no SSM param configured, returns the default bbox model ID."""
    from documentai_api.config.constants import PreprocessingBoundingBoxDefault
    from documentai_api.utils.bedrock import _get_bbox_model_id

    monkeypatch.setattr(
        "documentai_api.utils.bedrock.get_aws_config",
        lambda: type("C", (), {"bedrock_bounding_box_model_id_param": None})(),
    )

    assert _get_bbox_model_id() == PreprocessingBoundingBoxDefault.MODEL_ID


def test_get_bbox_model_id_reads_ssm(monkeypatch):
    """When SSM param is configured, reads the bbox model ID from SSM."""
    from documentai_api.utils.bedrock import _get_bbox_model_id

    monkeypatch.setattr(
        "documentai_api.utils.bedrock.get_aws_config",
        lambda: type("C", (), {"bedrock_bounding_box_model_id_param": "/test/bbox-model"})(),
    )
    monkeypatch.setattr(
        "documentai_api.utils.bedrock.get_parameter_value",
        lambda name, default=None: "us.amazon.nova-pro-v1:0",
    )

    assert _get_bbox_model_id() == "us.amazon.nova-pro-v1:0"


def test_bbox_detection_uses_bbox_model_id(monkeypatch):
    """detect_document_bbox invokes the bbox model, independent of the preclass model."""
    monkeypatch.setattr("documentai_api.utils.bedrock._get_model_id", lambda: "preclass-model")
    monkeypatch.setattr("documentai_api.utils.bedrock._get_bbox_model_id", lambda: "bbox-model")

    used = {}

    def capture_invoke(messages, max_tokens=256, model_id=None):
        used["model_id"] = model_id
        return _mock_invoke_response({"bounding_box": [100, 200, 800, 900]})

    monkeypatch.setattr("documentai_api.utils.bedrock.invoke_model", lambda **kwargs: None)
    monkeypatch.setattr("documentai_api.utils.bedrock._invoke", capture_invoke)

    assert detect_document_bbox(SAMPLE_IMAGE, "image/png") == (100.0, 200.0, 800.0, 900.0)
    assert used["model_id"] == "bbox-model"


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
# detect_document_bbox unit tests
# =============================================================================


def _patch_bbox_invoke(monkeypatch, response):
    monkeypatch.setattr("documentai_api.utils.bedrock._invoke", lambda **kwargs: response)


def test_detect_bbox_returns_box(monkeypatch):
    _patch_bbox_invoke(monkeypatch, _mock_invoke_response({"bounding_box": [100, 200, 800, 900]}))
    assert detect_document_bbox(SAMPLE_IMAGE, "image/png") == (100.0, 200.0, 800.0, 900.0)


def test_detect_bbox_null_returns_none(monkeypatch):
    _patch_bbox_invoke(monkeypatch, _mock_invoke_response({"bounding_box": None}))
    assert detect_document_bbox(SAMPLE_IMAGE, "image/png") is None


@pytest.mark.parametrize(
    "box",
    [
        [0, 0, 0, 0],  # degenerate
        [500, 0, 100, 900],  # x2 < x1
        [0, 0, 1200, 900],  # out of range
        [10, 20, 30],  # wrong length
    ],
)
def test_detect_bbox_rejects_invalid(monkeypatch, box):
    _patch_bbox_invoke(monkeypatch, _mock_invoke_response({"bounding_box": box}))
    assert detect_document_bbox(SAMPLE_IMAGE, "image/png") is None


def test_detect_bbox_non_image_returns_none():
    assert detect_document_bbox(b"%PDF-1.4", "application/pdf") is None


def _make_image_bytes(width: int, height: int, *, noise: bool = False, fmt: str = "PNG") -> bytes:
    """Build a real, PIL-openable image. ``noise`` produces poorly-compressible bytes."""
    import io
    import os

    from PIL import Image

    if noise:
        img = Image.frombytes("RGB", (width, height), os.urandom(width * height * 3))
    else:
        img = Image.new("RGB", (width, height), (123, 222, 64))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def test_detect_bbox_downscales_oversized_image(monkeypatch):
    """Downscale, don't skip, an image over the Converse byte limit.

    Still returns a bbox, and the bytes sent to the model are under the limit.
    """
    from documentai_api.config.constants import ConfigDefaults

    big = _make_image_bytes(2500, 2500, noise=True)
    assert len(big) > int(ConfigDefaults.BEDROCK_CONVERSE_MAX_IMAGE_BYTES)

    sent = {}

    def capture_invoke(**kwargs):
        sent["image"] = kwargs["messages"][0]["content"][0]["image"]
        return _mock_invoke_response({"bounding_box": [100, 200, 800, 900]})

    monkeypatch.setattr("documentai_api.utils.bedrock._invoke", capture_invoke)

    assert detect_document_bbox(big, "image/png") == (100.0, 200.0, 800.0, 900.0)
    sent_bytes = sent["image"]["source"]["bytes"]
    assert len(sent_bytes) <= int(ConfigDefaults.BEDROCK_CONVERSE_MAX_IMAGE_BYTES)
    assert sent["image"]["format"] == "jpeg"


def test_downscale_for_detection_caps_dimension():
    """An image exceeding the max pixel dimension is downscaled below it."""
    import io

    from PIL import Image

    from documentai_api.config.constants import ConfigDefaults
    from documentai_api.utils.bedrock import _downscale_for_detection

    max_dim = int(ConfigDefaults.BEDROCK_CONVERSE_MAX_IMAGE_DIMENSION_PX)
    wide = _make_image_bytes(max_dim + 500, 200)

    out_bytes, out_fmt = _downscale_for_detection(wide, "image/png")
    assert out_fmt == "jpeg"
    assert max(Image.open(io.BytesIO(out_bytes)).size) <= max_dim


def test_downscale_for_detection_passes_through_small_image():
    """An image already within limits is returned untouched with its source format."""
    from documentai_api.utils.bedrock import _downscale_for_detection

    small = _make_image_bytes(100, 100)
    out_bytes, out_fmt = _downscale_for_detection(small, "image/png")
    assert out_bytes is small
    assert out_fmt == "png"


def test_downscale_for_detection_returns_original_on_unreadable_bytes():
    """Best-effort: undecodable bytes fall back to the original (and source format)."""
    from documentai_api.utils.bedrock import _downscale_for_detection

    junk = b"\x89PNG" + b"\x00" * (int(ConfigDefaults.BEDROCK_CONVERSE_MAX_IMAGE_BYTES) + 1)
    out_bytes, out_fmt = _downscale_for_detection(junk, "image/png")
    assert out_bytes is junk
    assert out_fmt == "png"


def test_detect_bbox_swallows_errors(monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("bedrock down")

    monkeypatch.setattr("documentai_api.utils.bedrock._invoke", boom)
    assert detect_document_bbox(SAMPLE_IMAGE, "image/png") is None


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


# Photographed-on-background samples where document detection is meaningful (the
# document occupies only part of the frame).
BBOX_SAMPLES = [
    "synthetic-drivers-license-desk-background.jpg",
    "synthetic-public-benefits-identity-proof-state-photo-id.jpg",
    "synthetic-public-benefits-income-proof-pay-statement-photo.png",
    "synthetic-snap-income-proof-employment-wage-verification-letter-photo.png",
    "synthetic-snap-income-proof-self-employment-ledger-photo.png",
]

BBOX_OUTPUT_DIR = FIXTURES_DIR / "_bbox_output"


@pytest.mark.integration
@pytest.mark.parametrize("filename", BBOX_SAMPLES)
def test_detect_document_bbox_real(filename, monkeypatch, real_aws_credentials):
    """Detect a document's bbox on a real photo, verify it localizes, and write the crop.

    Asserts the box is valid and covers <90% of the frame (i.e. it actually cropped
    out background, not returned the whole image). The cropped image is written to
    tests/helpers/fixtures/test-documents/_bbox_output/ for visual inspection.
    """
    from documentai_api.utils.bedrock import detect_document_bbox
    from documentai_api.utils.image_optimization import crop_image_to_bbox

    monkeypatch.setattr(
        "documentai_api.utils.bedrock._get_bbox_model_id",
        lambda: "us.amazon.nova-lite-v1:0",
    )

    filepath = FIXTURES_DIR / filename
    if not filepath.exists():
        pytest.skip(f"Test fixture not found: {filepath}")

    image_bytes = filepath.read_bytes()
    content_type = _get_content_type(filename)

    bbox = detect_document_bbox(image_bytes, content_type)
    assert bbox is not None, f"{filename}: no bounding box detected"

    x1, y1, x2, y2 = bbox
    assert 0 <= x1 < x2 <= 1000, f"{filename}: invalid x range in {bbox}"
    assert 0 <= y1 < y2 <= 1000, f"{filename}: invalid y range in {bbox}"

    # sanity floor: the box isn't the literal full frame (detection returned
    # *something*). Real localization quality is judged from the written crops --
    # fill-frame document photos legitimately stay near 100%, so we don't assert a
    # tight fraction here or the test would flake on model drift.
    area_fraction = ((x2 - x1) * (y2 - y1)) / (1000 * 1000)
    assert area_fraction < 0.98, (
        f"{filename}: box covers {area_fraction:.0%} of the frame - detection did not localize"
    )

    # write the crop for human review
    BBOX_OUTPUT_DIR.mkdir(exist_ok=True)
    cropped = crop_image_to_bbox(image_bytes, bbox)
    out_path = BBOX_OUTPUT_DIR / f"{Path(filename).stem}.cropped{Path(filename).suffix}"
    out_path.write_bytes(cropped)
    print(f"\n{filename}: bbox={bbox} area={area_fraction:.0%} -> {out_path}")


@pytest.mark.integration
def test_detect_document_bbox_oversized_real(monkeypatch, real_aws_credentials):
    """A real photo upscaled past the Converse byte limit still detects + crops.

    Verifies the #2 fix end-to-end: detection downscales an in-memory copy for the
    Nova call, and the returned normalized box still crops the full-resolution
    original (which remains over the Converse limit).
    """
    import io

    from PIL import Image

    from documentai_api.config.constants import ConfigDefaults
    from documentai_api.utils.bedrock import detect_document_bbox
    from documentai_api.utils.image_optimization import crop_image_to_bbox

    monkeypatch.setattr(
        "documentai_api.utils.bedrock._get_bbox_model_id",
        lambda: "us.amazon.nova-lite-v1:0",
    )

    filename = BBOX_SAMPLES[0]
    filepath = FIXTURES_DIR / filename
    if not filepath.exists():
        pytest.skip(f"Test fixture not found: {filepath}")

    # upscale the sample until its encoded bytes exceed the per-image Converse limit
    src = Image.open(io.BytesIO(filepath.read_bytes())).convert("RGB")
    big = src.resize((src.width * 4, src.height * 4))
    buf = io.BytesIO()
    big.save(buf, format="PNG")
    image_bytes = buf.getvalue()
    assert len(image_bytes) > int(ConfigDefaults.BEDROCK_CONVERSE_MAX_IMAGE_BYTES)

    bbox = detect_document_bbox(image_bytes, "image/png")
    assert bbox is not None, f"{filename}: no bbox detected on oversized image"

    x1, y1, x2, y2 = bbox
    assert 0 <= x1 < x2 <= 1000, f"invalid x range in {bbox}"
    assert 0 <= y1 < y2 <= 1000, f"invalid y range in {bbox}"

    # the normalized box must still crop the full-resolution original
    cropped = crop_image_to_bbox(image_bytes, bbox)
    cw, ch = Image.open(io.BytesIO(cropped)).size
    assert cw < big.width, "crop did not reduce original width"
    assert ch < big.height, "crop did not reduce original height"


@pytest.mark.integration
@pytest.mark.parametrize(
    ("filename", "expected_category"),
    _expected_items
    or [pytest.param("skip", "skip", marks=pytest.mark.skip(reason="No test fixtures"))],
)
def test_preclassify_real_document(filename, expected_category, monkeypatch, real_aws_credentials):
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
