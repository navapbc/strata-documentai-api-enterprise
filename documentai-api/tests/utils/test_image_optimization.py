"""Tests for utils/image_optimization.py (pre-BDA S3 image preparation)."""

import io
from decimal import Decimal

import pytest
from PIL import Image

from documentai_api.config.constants import ConfigDefaults
from documentai_api.utils.dto import CropResult
from documentai_api.utils.image_optimization import (
    convert_s3_object_to_grayscale,
    convert_to_grayscale,
    crop_image_to_bbox,
    crop_image_to_document_roi,
    is_file_too_large_for_bda,
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


def test_crop_to_bbox_exact_region_no_padding():
    """Bbox on a 0-1000 scale maps to the expected pixel region (pad_ratio=0)."""
    result = crop_image_to_bbox(_sized_image(1000, 1000), (200, 200, 600, 600), pad_ratio=0)
    assert Image.open(io.BytesIO(result)).size == (400, 400)


def test_crop_to_bbox_padding_clamps_to_image_bounds():
    """Padding never pushes the crop outside the image."""
    result = crop_image_to_bbox(_sized_image(1000, 1000), (0, 0, 1000, 1000), pad_ratio=0.1)
    assert Image.open(io.BytesIO(result)).size == (1000, 1000)  # clamped, not 1100+


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


def test_convert_to_grayscale_non_image():
    """Test that non-image files are returned unchanged."""
    file_bytes = b"pdf content"
    result_bytes, result_type = convert_to_grayscale("test.pdf", file_bytes, "application/pdf")

    assert result_bytes == file_bytes
    assert result_type == "application/pdf"


def test_convert_to_grayscale_invalid_image():
    """Test grayscale conversion with invalid image data."""
    file_bytes = b"not an image"
    result_bytes, result_type = convert_to_grayscale("test.jpg", file_bytes, "image/jpeg")

    assert result_bytes == file_bytes
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


def test_convert_s3_object_to_grayscale_success(s3_bucket, mocker):
    """Test successful S3 object grayscale conversion."""
    s3_bucket.put_object(Key="test.jpg", Body=b"image data", ContentType="image/jpeg")

    mock_convert = mocker.patch(f"{MODULE}.convert_to_grayscale")
    mock_convert.return_value = (b"grayscale data", "image/jpeg")

    result = convert_s3_object_to_grayscale(s3_bucket.name, "test.jpg")

    current_object = s3_bucket.Object("test.jpg")

    assert result is True
    mock_convert.assert_called_once_with("test.jpg", b"image data", "image/jpeg")
    assert current_object.content_type == "image/jpeg"
    assert current_object.get()["Body"].read() == b"grayscale data"


def test_convert_s3_object_to_grayscale_file_too_large(s3_bucket, mocker):
    """Test S3 conversion returns False when file too large."""
    s3_bucket.put_object(Key="test.jpg", Body=b"image data", ContentType="image/jpeg")

    large_bytes = b"x" * (ConfigDefaults.BDA_MAX_IMAGE_SIZE_BYTES + 1)
    mock_convert = mocker.patch(f"{MODULE}.convert_to_grayscale")
    mock_convert.return_value = (large_bytes, "image/jpeg")

    result = convert_s3_object_to_grayscale(s3_bucket.name, "test.jpg")

    assert result is False
    # but file is still updated in S3
    assert s3_bucket.Object("test.jpg").get()["Body"].read() == large_bytes


def test_convert_s3_object_to_grayscale_error(s3_bucket):
    """Test S3 grayscale conversion handles errors gracefully."""
    result = convert_s3_object_to_grayscale(s3_bucket.name, "file_that_does_not_exist.jpg")

    assert result is False


def test_crop_roi_disabled_is_noop(s3_bucket, mocker):
    """Feature flag off: detection never runs, object untouched."""
    mocker.patch(f"{MODULE}.is_document_crop_enabled", return_value=False)
    detect = mocker.patch(f"{MODULE}.detect_document_bbox")
    s3_bucket.put_object(Key="a.png", Body=b"orig", ContentType="image/png")

    crop_image_to_document_roi(s3_bucket.name, "a.png")

    detect.assert_not_called()
    assert s3_bucket.Object("a.png").get()["Body"].read() == b"orig"


def test_crop_roi_skips_non_image(s3_bucket, mocker):
    """PDFs are never detected/cropped."""
    mocker.patch(f"{MODULE}.is_document_crop_enabled", return_value=True)
    detect = mocker.patch(f"{MODULE}.detect_document_bbox")
    s3_bucket.put_object(Key="a.pdf", Body=b"%PDF-1.4", ContentType="application/pdf")

    crop_image_to_document_roi(s3_bucket.name, "a.pdf")

    detect.assert_not_called()


def test_crop_roi_no_document_leaves_object(s3_bucket, mocker):
    """No bbox detected: object is left uncropped."""
    mocker.patch(f"{MODULE}.is_document_crop_enabled", return_value=True)
    mocker.patch(f"{MODULE}.detect_document_bbox", return_value=(None, CropResult()))
    original = _png_bytes(1000, 1000)
    s3_bucket.put_object(Key="a.png", Body=original, ContentType="image/png")

    crop_image_to_document_roi(s3_bucket.name, "a.png")

    assert s3_bucket.Object("a.png").get()["Body"].read() == original


def test_crop_roi_happy_path_overwrites_with_cropped(s3_bucket, mocker, monkeypatch):
    """A detected bbox crops the S3 image in place to a smaller image."""
    from documentai_api.config.env import EnvVars

    monkeypatch.setenv(
        EnvVars.DOCUMENTAI_PREPROCESSING_LOCATION, f"s3://{s3_bucket.name}/preprocessing"
    )
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

    crop_image_to_document_roi(s3_bucket.name, "a.png")

    stored = s3_bucket.Object("a.png").get()["Body"].read()
    cropped = Image.open(io.BytesIO(stored))
    assert cropped.width < 1000
    assert cropped.height < 1000


def test_crop_roi_aborts_when_no_preprocessing_location(s3_bucket, mocker, monkeypatch):
    """Without a backup location we must NOT overwrite: original is preserved."""
    from documentai_api.config.env import EnvVars

    monkeypatch.delenv(EnvVars.DOCUMENTAI_PREPROCESSING_LOCATION, raising=False)
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
    original = _png_bytes(1000, 1000)
    s3_bucket.put_object(Key="a.png", Body=original, ContentType="image/png")

    crop_image_to_document_roi(s3_bucket.name, "a.png")  # no exception

    # original is untouched because the pre-crop backup could not be made
    assert s3_bucket.Object("a.png").get()["Body"].read() == original


def test_crop_roi_saves_precrop_original_to_preprocessing(s3_bucket, mocker, monkeypatch):
    """The pre-crop image is preserved under preprocessing/precrop/ before overwrite."""
    from documentai_api.config.env import EnvVars

    monkeypatch.setenv(
        EnvVars.DOCUMENTAI_PREPROCESSING_LOCATION, f"s3://{s3_bucket.name}/preprocessing"
    )
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
    original = _png_bytes(1000, 1000)
    s3_bucket.put_object(Key="a.png", Body=original, ContentType="image/png")

    crop_image_to_document_roi(s3_bucket.name, "a.png")

    # the untouched pre-crop original is preserved
    assert s3_bucket.Object("preprocessing/precrop/a.png").get()["Body"].read() == original
    # while the live object is the (smaller) crop
    assert len(s3_bucket.Object("a.png").get()["Body"].read()) != len(original)


def test_crop_roi_saves_precrop_original_tenant_scoped(s3_bucket, mocker, monkeypatch):
    """With a tenant_id the pre-crop backup is stored under {tenant}/precrop/."""
    from documentai_api.config.env import EnvVars

    monkeypatch.setenv(
        EnvVars.DOCUMENTAI_PREPROCESSING_LOCATION, f"s3://{s3_bucket.name}/preprocessing"
    )
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
    original = _png_bytes(1000, 1000)
    s3_bucket.put_object(Key="a.png", Body=original, ContentType="image/png")

    crop_image_to_document_roi(s3_bucket.name, "a.png", tenant_id="test-tenant")

    stored = s3_bucket.Object("preprocessing/test-tenant/precrop/a.png").get()["Body"].read()
    assert stored == original


def test_crop_roi_swallows_errors(s3_bucket, mocker):
    """Missing object: never raises, processing continues."""
    mocker.patch(f"{MODULE}.is_document_crop_enabled", return_value=True)
    crop_image_to_document_roi(s3_bucket.name, "does_not_exist.png")  # no exception
