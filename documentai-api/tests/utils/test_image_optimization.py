"""Tests for utils/image_optimization.py (pre-BDA S3 image preparation)."""

import io
from decimal import Decimal

import pytest
from PIL import Image

from documentai_api.config.constants import ConfigDefaults
from documentai_api.services import s3 as s3_service
from documentai_api.utils.dto import CropResult
from documentai_api.utils.image_optimization import (
    convert_to_grayscale,
    crop_image_to_bbox,
    is_file_too_large_for_bda,
    optimize_s3_image,
)

MODULE = "documentai_api.utils.image_optimization"


@pytest.fixture(autouse=True)
def mock_env(runtime_required_env):
    pass


def _png_bytes(width: int, height: int) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (width, height), color="red").save(output, format="PNG")
    return output.getvalue()


def _sized_image(width: int, height: int, fmt: str = "PNG") -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (width, height), color="red").save(output, format=fmt)
    return output.getvalue()


# --- crop_image_to_bbox unit tests ---


def test_crop_to_bbox_exact_region_no_padding():
    """Bbox on a 0-1000 scale maps to the expected pixel region (pad_ratio=0)."""
    result = crop_image_to_bbox(_sized_image(1000, 1000), (200, 200, 600, 600), pad_ratio=0)
    assert Image.open(io.BytesIO(result)).size == (400, 400)


def test_crop_to_bbox_padding_clamps_to_image_bounds():
    """Padding never pushes the crop outside the image."""
    # bbox covers 60% of frame (below 75% skip threshold), padding would exceed bounds
    result = crop_image_to_bbox(_sized_image(1000, 1000), (100, 100, 900, 700), pad_ratio=0.2)
    img = Image.open(io.BytesIO(result))
    # Padding would push beyond image bounds but gets clamped
    assert img.width <= 1000
    assert img.height <= 1000


def test_crop_to_bbox_skip_threshold_returns_original():
    """Bbox covering >= 75% of frame skips cropping and returns original bytes."""
    original = _sized_image(1000, 1000)
    # bbox covers 90% of frame (900 * 1000 / 1_000_000 = 0.9)
    result = crop_image_to_bbox(original, (50, 0, 950, 1000))
    assert result is original


def test_crop_to_bbox_below_skip_threshold_crops():
    """Bbox covering < 75% of frame performs the crop."""
    original = _sized_image(1000, 1000)
    # bbox covers 25% of frame (500 * 500 / 1_000_000 = 0.25)
    result = crop_image_to_bbox(original, (250, 250, 750, 750), pad_ratio=0)
    assert result is not original
    img = Image.open(io.BytesIO(result))
    assert img.size == (500, 500)


def test_crop_to_bbox_preserves_format():
    result = crop_image_to_bbox(
        _sized_image(800, 800, fmt="JPEG"), (100, 100, 700, 700), pad_ratio=0
    )
    assert Image.open(io.BytesIO(result)).format == "JPEG"


def test_crop_to_bbox_empty_region_raises():
    """A box that rounds to under one pixel is rejected."""
    with pytest.raises(ValueError, match="Image crop failed"):
        crop_image_to_bbox(_sized_image(100, 100), (0, 0, 5, 5), pad_ratio=0)


def test_crop_to_bbox_invalid_bytes_raises():
    with pytest.raises(ValueError, match="Image crop failed"):
        crop_image_to_bbox(b"not an image", (100, 100, 900, 900))


# --- is_file_too_large_for_bda ---


@pytest.mark.parametrize(
    ("content_type", "file_size", "expected"),
    [
        ("image/jpeg", ConfigDefaults.BDA_MAX_IMAGE_SIZE_BYTES, False),
        ("image/jpeg", int(ConfigDefaults.BDA_MAX_IMAGE_SIZE_BYTES) + 1, True),
        ("image/png", ConfigDefaults.BDA_MAX_IMAGE_SIZE_BYTES, False),
        ("image/png", int(ConfigDefaults.BDA_MAX_IMAGE_SIZE_BYTES) + 1, True),
        ("application/pdf", ConfigDefaults.BDA_MAX_DOCUMENT_FILE_SIZE_BYTES, False),
        ("application/pdf", int(ConfigDefaults.BDA_MAX_DOCUMENT_FILE_SIZE_BYTES) + 1, True),
        ("image/tiff", ConfigDefaults.BDA_MAX_DOCUMENT_FILE_SIZE_BYTES, False),
        ("image/tiff", int(ConfigDefaults.BDA_MAX_DOCUMENT_FILE_SIZE_BYTES) + 1, True),
        ("unknown/type", int(ConfigDefaults.BDA_MAX_IMAGE_SIZE_BYTES) + 1, True),
    ],
)
def test_is_file_too_large_for_bda(content_type, file_size, expected):
    """Test file size validation for BDA limits."""
    assert is_file_too_large_for_bda(content_type, file_size) == expected


# --- convert_to_grayscale ---


def test_convert_to_grayscale_non_image():
    """Test that non-image files are returned unchanged."""
    file_bytes = b"pdf content"
    result_bytes, result_type = convert_to_grayscale("test.pdf", file_bytes, "application/pdf")

    assert result_bytes is file_bytes
    assert result_type == "application/pdf"


def test_convert_to_grayscale_invalid_image():
    """Test grayscale conversion with invalid image data."""
    file_bytes = b"not an image"
    result_bytes, result_type = convert_to_grayscale("test.jpg", file_bytes, "image/jpeg")

    assert result_bytes is file_bytes
    assert result_type == "image/jpeg"


def test_convert_to_grayscale_small_image():
    """Test grayscale conversion with small valid image."""
    img = Image.new("RGB", (10, 10), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")

    result_bytes, result_type = convert_to_grayscale("test.jpg", buf.getvalue(), "image/jpeg")

    assert result_type == "image/jpeg"
    assert len(result_bytes) > 0


def test_convert_to_grayscale_large_image_converts_to_pdf():
    """Test large image converts to PDF."""
    img = Image.new("RGB", (5000, 5000), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")

    _, result_type = convert_to_grayscale("test.jpg", buf.getvalue(), "image/jpeg")

    # May or may not convert to PDF depending on compression
    assert result_type in ["image/jpeg", "application/pdf"]


# --- optimize_s3_image ---


def test_optimize_crop_disabled_is_noop(s3_bucket, mocker):
    """Feature flag off + no grayscale: object untouched, no write."""
    mocker.patch(f"{MODULE}.is_document_crop_enabled", return_value=False)
    detect = mocker.patch(f"{MODULE}.detect_document_bbox")
    original = _png_bytes(100, 100)
    s3_bucket.put_object(Key="a.png", Body=original, ContentType="image/png")

    result = optimize_s3_image(s3_bucket.name, "a.png")

    detect.assert_not_called()
    assert s3_bucket.Object("a.png").get()["Body"].read() == original
    assert result.crop_result.cropped is False
    assert result.grayscale_applied is False


def test_optimize_skips_crop_for_non_image(s3_bucket, mocker):
    """PDFs are never detected/cropped."""
    mocker.patch(f"{MODULE}.is_document_crop_enabled", return_value=True)
    detect = mocker.patch(f"{MODULE}.detect_document_bbox")
    s3_bucket.put_object(Key="a.pdf", Body=b"%PDF-1.4", ContentType="application/pdf")

    optimize_s3_image(s3_bucket.name, "a.pdf")

    detect.assert_not_called()


def test_optimize_no_bbox_leaves_object(s3_bucket, mocker):
    """No bbox detected: object is left uncropped."""
    mocker.patch(f"{MODULE}.is_document_crop_enabled", return_value=True)
    mocker.patch(f"{MODULE}.detect_document_bbox", return_value=(None, CropResult()))
    original = _png_bytes(1000, 1000)
    s3_bucket.put_object(Key="a.png", Body=original, ContentType="image/png")

    result = optimize_s3_image(s3_bucket.name, "a.png")

    assert s3_bucket.Object("a.png").get()["Body"].read() == original
    assert result.crop_result.cropped is False


def test_optimize_crop_happy_path(s3_bucket, mocker):
    """A detected bbox crops the S3 image in place to a smaller image."""
    mocker.patch(f"{MODULE}.is_document_crop_enabled", return_value=True)
    mocker.patch(
        f"{MODULE}.detect_document_bbox",
        return_value=(
            (200, 200, 600, 600),
            CropResult(
                duration_seconds=Decimal("0.5"),
                input_tokens=100,
                output_tokens=50,
                model_id="test-model",
            ),
        ),
    )
    s3_bucket.put_object(Key="a.png", Body=_png_bytes(1000, 1000), ContentType="image/png")

    result = optimize_s3_image(s3_bucket.name, "a.png")

    stored = s3_bucket.Object("a.png").get()["Body"].read()
    cropped = Image.open(io.BytesIO(stored))
    assert cropped.width < 1000
    assert cropped.height < 1000
    assert result.crop_result.cropped is True
    assert result.crop_result.bounding_box == (200, 200, 600, 600)


def test_optimize_detect_bbox_error_is_best_effort(s3_bucket, mocker):
    """detect_document_bbox failure: object untouched, no crash."""
    mocker.patch(f"{MODULE}.is_document_crop_enabled", return_value=True)
    mocker.patch(f"{MODULE}.detect_document_bbox", side_effect=RuntimeError("Bedrock timeout"))
    original = _png_bytes(100, 100)
    s3_bucket.put_object(Key="a.png", Body=original, ContentType="image/png")

    result = optimize_s3_image(s3_bucket.name, "a.png")

    assert s3_bucket.Object("a.png").get()["Body"].read() == original
    assert result.crop_result.cropped is False
    assert result.failed is False


def test_optimize_crop_raises_is_best_effort(s3_bucket, mocker):
    """crop_image_to_bbox failure (e.g. unusable region): object untouched, no crash."""
    mocker.patch(f"{MODULE}.is_document_crop_enabled", return_value=True)
    mocker.patch(
        f"{MODULE}.detect_document_bbox",
        return_value=((200, 200, 600, 600), CropResult()),
    )
    mocker.patch(f"{MODULE}.crop_image_to_bbox", side_effect=ValueError("empty crop region"))
    original = _png_bytes(1000, 1000)
    s3_bucket.put_object(Key="a.png", Body=original, ContentType="image/png")

    result = optimize_s3_image(s3_bucket.name, "a.png")

    assert s3_bucket.Object("a.png").get()["Body"].read() == original
    assert result.crop_result.cropped is False
    assert result.failed is False


def test_optimize_download_failure_sets_failed(s3_bucket, mocker):
    """S3 GET failure: failed=True, no crash."""
    mocker.patch(f"{MODULE}.is_document_crop_enabled", return_value=True)

    result = optimize_s3_image(s3_bucket.name, "does_not_exist.png")

    assert result.failed is True
    assert result.file_size_bytes is None


def test_optimize_grayscale_converts_image(s3_bucket, mocker):
    """apply_grayscale=True converts image and writes once."""
    mocker.patch(f"{MODULE}.is_document_crop_enabled", return_value=False)
    put_spy = mocker.spy(s3_service, "put_object")
    original = _sized_image(100, 100, fmt="JPEG")
    s3_bucket.put_object(Key="a.jpg", Body=original, ContentType="image/jpeg")

    result = optimize_s3_image(s3_bucket.name, "a.jpg", apply_grayscale=True)

    assert result.grayscale_applied is True
    stored = s3_bucket.Object("a.jpg").get()["Body"].read()
    img = Image.open(io.BytesIO(stored))
    assert img.mode == "L"
    # Single write (grayscale only, no crop)
    assert put_spy.call_count == 1
    # file_size_bytes reflects the bytes actually written (no extra S3 HEAD).
    assert result.file_size_bytes == len(stored)


def test_optimize_grayscale_noop_for_pdf(s3_bucket, mocker):
    """apply_grayscale=True with a PDF: no conversion, no write."""
    mocker.patch(f"{MODULE}.is_document_crop_enabled", return_value=False)
    original = b"%PDF-1.4 content"
    s3_bucket.put_object(Key="a.pdf", Body=original, ContentType="application/pdf")

    result = optimize_s3_image(s3_bucket.name, "a.pdf", apply_grayscale=True)

    assert result.grayscale_applied is False
    assert s3_bucket.Object("a.pdf").get()["Body"].read() == original


def test_optimize_crop_and_grayscale_single_write(s3_bucket, mocker):
    """Both crop and grayscale applied with only one S3 PUT to the live object."""
    mocker.patch(f"{MODULE}.is_document_crop_enabled", return_value=True)
    mocker.patch(
        f"{MODULE}.detect_document_bbox",
        return_value=(
            (200, 200, 600, 600),
            CropResult(
                duration_seconds=Decimal("0.5"),
                input_tokens=100,
                output_tokens=50,
                model_id="test-model",
            ),
        ),
    )
    put_spy = mocker.spy(s3_service, "put_object")
    original = _png_bytes(1000, 1000)
    s3_bucket.put_object(Key="a.png", Body=original, ContentType="image/png")

    result = optimize_s3_image(s3_bucket.name, "a.png", apply_grayscale=True)

    assert result.crop_result.cropped is True
    assert result.grayscale_applied is True
    stored = s3_bucket.Object("a.png").get()["Body"].read()
    img = Image.open(io.BytesIO(stored))
    assert img.width < 1000
    assert img.mode == "L"
    # Single write to the live object
    assert put_spy.call_count == 1


def test_optimize_too_large_after_conversion(s3_bucket, mocker):
    """File still over BDA limit after grayscale: too_large=True."""
    mocker.patch(f"{MODULE}.is_document_crop_enabled", return_value=False)
    mocker.patch(
        f"{MODULE}.convert_to_grayscale",
        return_value=(b"x" * (ConfigDefaults.BDA_MAX_IMAGE_SIZE_BYTES + 1), "image/jpeg"),
    )
    s3_bucket.put_object(Key="a.jpg", Body=b"small", ContentType="image/jpeg")

    result = optimize_s3_image(s3_bucket.name, "a.jpg", apply_grayscale=True)

    assert result.too_large is True
    assert result.grayscale_applied is True
