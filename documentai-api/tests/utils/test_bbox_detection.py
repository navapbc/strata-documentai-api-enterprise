"""Tests for document bounding-box detection utilities."""

import json
from pathlib import Path

import pytest

from documentai_api.config.constants import ConfigDefaults
from documentai_api.utils.bbox_detection import detect_document_bbox

SAMPLE_IMAGE = b"\x89PNG\r\n" + b"\x00" * 100


def _mock_invoke_response(parsed: dict) -> dict:
    return {
        "output": {"message": {"content": [{"text": json.dumps(parsed)}]}},
        "usage": {"inputTokens": 100, "outputTokens": 50},
    }


def _patch_bbox_invoke(monkeypatch, response):
    monkeypatch.setattr(
        "documentai_api.utils.bbox_detection.invoke_model", lambda **kwargs: response
    )


def _make_image_bytes(width: int, height: int, *, noise: bool = False, fmt: str = "PNG") -> bytes:
    """Build a real, PIL-openable image."""
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


# =============================================================================
# Unit tests
# =============================================================================


def test_detect_bbox_returns_box(monkeypatch):
    _patch_bbox_invoke(monkeypatch, _mock_invoke_response({"bounding_box": [100, 200, 800, 900]}))
    bbox, _ = detect_document_bbox(SAMPLE_IMAGE, "image/png")
    assert bbox == (100.0, 200.0, 800.0, 900.0)


def test_detect_bbox_null_returns_none(monkeypatch):
    _patch_bbox_invoke(monkeypatch, _mock_invoke_response({"bounding_box": None}))
    bbox, _ = detect_document_bbox(SAMPLE_IMAGE, "image/png")
    assert bbox is None


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
    bbox, _ = detect_document_bbox(SAMPLE_IMAGE, "image/png")
    assert bbox is None


def test_detect_bbox_non_image_returns_none():
    bbox, _ = detect_document_bbox(b"%PDF-1.4", "application/pdf")
    assert bbox is None


def test_detect_bbox_downscales_oversized_image(monkeypatch):
    """Downscale, don't skip, an image over the Converse byte limit."""
    big = _make_image_bytes(2500, 2500, noise=True)
    assert len(big) > int(ConfigDefaults.BEDROCK_CONVERSE_MAX_IMAGE_BYTES)

    sent = {}

    def capture_invoke(**kwargs):
        sent["image"] = kwargs["messages"][0]["content"][0]["image"]
        return _mock_invoke_response({"bounding_box": [100, 200, 800, 900]})

    monkeypatch.setattr("documentai_api.utils.bbox_detection.invoke_model", capture_invoke)

    bbox, _ = detect_document_bbox(big, "image/png")
    assert bbox == (100.0, 200.0, 800.0, 900.0)
    sent_bytes = sent["image"]["source"]["bytes"]
    assert len(sent_bytes) <= int(ConfigDefaults.BEDROCK_CONVERSE_MAX_IMAGE_BYTES)
    assert sent["image"]["format"] == "jpeg"


def test_downscale_for_detection_caps_dimension():
    """An image exceeding the max pixel dimension is downscaled below it."""
    import io

    from PIL import Image

    from documentai_api.utils.bbox_detection import _downscale_for_detection

    max_dim = int(ConfigDefaults.BEDROCK_CONVERSE_MAX_IMAGE_DIMENSION_PX)
    wide = _make_image_bytes(max_dim + 500, 200)

    out_bytes, out_fmt = _downscale_for_detection(wide, "image/png")
    assert out_fmt == "jpeg"
    assert max(Image.open(io.BytesIO(out_bytes)).size) <= max_dim


def test_downscale_for_detection_passes_through_small_image():
    """An image already within limits is returned untouched with its source format."""
    from documentai_api.utils.bbox_detection import _downscale_for_detection

    small = _make_image_bytes(100, 100)
    out_bytes, out_fmt = _downscale_for_detection(small, "image/png")
    assert out_bytes is small
    assert out_fmt == "png"


def test_downscale_for_detection_returns_original_on_unreadable_bytes():
    """Best-effort: undecodable bytes fall back to the original."""
    from documentai_api.utils.bbox_detection import _downscale_for_detection

    junk = b"\x89PNG" + b"\x00" * (int(ConfigDefaults.BEDROCK_CONVERSE_MAX_IMAGE_BYTES) + 1)
    out_bytes, out_fmt = _downscale_for_detection(junk, "image/png")
    assert out_bytes is junk
    assert out_fmt == "png"


def test_detect_bbox_swallows_errors(monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("bedrock down")

    monkeypatch.setattr("documentai_api.utils.bbox_detection.invoke_model", boom)
    bbox, _ = detect_document_bbox(SAMPLE_IMAGE, "image/png")
    assert bbox is None


def test_get_bbox_model_id_uses_default(monkeypatch):
    """When no SSM param configured, returns the default bbox model ID."""
    from documentai_api.config.constants import PreprocessingBoundingBoxDefault
    from documentai_api.utils.bbox_detection import _get_bbox_model_id

    monkeypatch.setattr(
        "documentai_api.utils.bbox_detection.get_aws_config",
        lambda: type("C", (), {"bedrock_bounding_box_model_id_param": None})(),
    )

    assert _get_bbox_model_id() == PreprocessingBoundingBoxDefault.MODEL_ID


def test_get_bbox_model_id_reads_ssm(monkeypatch):
    """When SSM param is configured, reads the bbox model ID from SSM."""
    from documentai_api.utils.bbox_detection import _get_bbox_model_id

    monkeypatch.setattr(
        "documentai_api.utils.bbox_detection.get_aws_config",
        lambda: type("C", (), {"bedrock_bounding_box_model_id_param": "/test/bbox-model"})(),
    )
    monkeypatch.setattr(
        "documentai_api.utils.bbox_detection.get_parameter_value",
        lambda name, default=None: "us.amazon.nova-pro-v1:0",
    )

    assert _get_bbox_model_id() == "us.amazon.nova-pro-v1:0"


def test_bbox_detection_uses_bbox_model_id(monkeypatch):
    """detect_document_bbox invokes the bbox model, independent of the preclass model."""
    monkeypatch.setattr(
        "documentai_api.utils.bbox_detection._get_bbox_model_id", lambda: "bbox-model"
    )

    used = {}

    def capture_invoke(**kwargs):
        used["model_id"] = kwargs["model_id"]
        return _mock_invoke_response({"bounding_box": [100, 200, 800, 900]})

    monkeypatch.setattr("documentai_api.utils.bbox_detection.invoke_model", capture_invoke)

    bbox, _ = detect_document_bbox(SAMPLE_IMAGE, "image/png")
    assert bbox == (100.0, 200.0, 800.0, 900.0)
    assert used["model_id"] == "bbox-model"


# =============================================================================
# Integration tests - call real Bedrock API
# =============================================================================

FIXTURES_DIR = Path(__file__).parent.parent / "helpers" / "fixtures" / "test-documents"

CONTENT_TYPE_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".pdf": "application/pdf",
}


def _get_content_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return CONTENT_TYPE_MAP.get(ext, "application/octet-stream")


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
    """Detect a document's bbox on a real photo, verify it localizes, and write the crop."""
    from documentai_api.utils.bbox_detection import detect_document_bbox
    from documentai_api.utils.image_optimization import crop_image_to_bbox

    monkeypatch.setattr(
        "documentai_api.utils.bbox_detection._get_bbox_model_id",
        lambda: "us.amazon.nova-lite-v1:0",
    )

    filepath = FIXTURES_DIR / filename
    if not filepath.exists():
        pytest.skip(f"Test fixture not found: {filepath}")

    image_bytes = filepath.read_bytes()
    content_type = _get_content_type(filename)

    bbox, metrics = detect_document_bbox(image_bytes, content_type)
    assert bbox is not None, f"{filename}: no bounding box detected"

    assert metrics.model_id == "us.amazon.nova-lite-v1:0"
    assert metrics.duration_seconds is not None
    assert metrics.duration_seconds > 0
    assert metrics.input_tokens is not None
    assert metrics.input_tokens > 0
    assert metrics.output_tokens is not None
    assert metrics.output_tokens > 0

    x1, y1, x2, y2 = bbox
    assert 0 <= x1 < x2 <= 1000, f"{filename}: invalid x range in {bbox}"
    assert 0 <= y1 < y2 <= 1000, f"{filename}: invalid y range in {bbox}"

    area_fraction = ((x2 - x1) * (y2 - y1)) / (1000 * 1000)
    assert area_fraction < 0.98, (
        f"{filename}: box covers {area_fraction:.0%} of the frame - detection did not localize"
    )

    BBOX_OUTPUT_DIR.mkdir(exist_ok=True)
    cropped = crop_image_to_bbox(image_bytes, bbox)
    out_path = BBOX_OUTPUT_DIR / f"{Path(filename).stem}.cropped{Path(filename).suffix}"
    out_path.write_bytes(cropped)
    print(f"\n{filename}: bbox={bbox} area={area_fraction:.0%} -> {out_path}")


@pytest.mark.integration
def test_detect_document_bbox_oversized_real(monkeypatch, real_aws_credentials):
    """A real photo upscaled past the Converse byte limit still detects + crops."""
    import io

    from PIL import Image

    from documentai_api.utils.bbox_detection import detect_document_bbox
    from documentai_api.utils.image_optimization import crop_image_to_bbox

    monkeypatch.setattr(
        "documentai_api.utils.bbox_detection._get_bbox_model_id",
        lambda: "us.amazon.nova-lite-v1:0",
    )

    filename = BBOX_SAMPLES[0]
    filepath = FIXTURES_DIR / filename
    if not filepath.exists():
        pytest.skip(f"Test fixture not found: {filepath}")

    src = Image.open(io.BytesIO(filepath.read_bytes())).convert("RGB")
    big = src.resize((src.width * 4, src.height * 4))
    buf = io.BytesIO()
    big.save(buf, format="PNG")
    image_bytes = buf.getvalue()
    assert len(image_bytes) > int(ConfigDefaults.BEDROCK_CONVERSE_MAX_IMAGE_BYTES)

    bbox, _ = detect_document_bbox(image_bytes, "image/png")
    assert bbox is not None, f"{filename}: no bbox detected on oversized image"

    x1, y1, x2, y2 = bbox
    assert 0 <= x1 < x2 <= 1000, f"invalid x range in {bbox}"
    assert 0 <= y1 < y2 <= 1000, f"invalid y range in {bbox}"

    cropped = crop_image_to_bbox(image_bytes, bbox)
    cw, ch = Image.open(io.BytesIO(cropped)).size
    assert cw < big.width, "crop did not reduce original width"
    assert ch < big.height, "crop did not reduce original height"
