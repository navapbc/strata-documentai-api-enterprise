"""Prepare an uploaded S3 image for Bedrock Data Automation.

These helpers download an S3 object, transform it (crop to the document ROI,
grayscale, downsize), and overwrite it in place before BDA is invoked. They are
best-effort: a failure leaves the original object untouched so BDA still runs.
"""

import io
from decimal import Decimal

from PIL import Image

from documentai_api.config.constants import ConfigDefaults, FileValidation
from documentai_api.logging import get_logger
from documentai_api.services import s3 as s3_service
from documentai_api.utils.bedrock import detect_document_bbox
from documentai_api.utils.dto import CropResult, OptimizationResult
from documentai_api.utils.ssm import is_document_crop_enabled

logger = get_logger(__name__)


def crop_image_to_bbox(
    image_bytes: bytes,
    bbox: tuple[float, float, float, float],
    *,
    pad_ratio: float = 0.03,
) -> bytes:
    """Crop an image to a bounding box given on a 0-1000 normalized scale.

    The box is rescaled to pixels, padded by ``pad_ratio`` of each dimension (so a
    slightly-loose detection never clips the document), and clamped to the image.
    The output is re-encoded in the source image's format.

    Raises:
        ValueError: if the image can't be opened or the box is unusable.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        fmt = img.format or "PNG"
        width, height = img.size

        x1, y1, x2, y2 = bbox
        pad_x = (x2 - x1) * pad_ratio
        pad_y = (y2 - y1) * pad_ratio

        left = max(0, int((x1 - pad_x) / 1000 * width))
        top = max(0, int((y1 - pad_y) / 1000 * height))
        right = min(width, int((x2 + pad_x) / 1000 * width))
        bottom = min(height, int((y2 + pad_y) / 1000 * height))

        if right <= left or bottom <= top:
            raise ValueError(f"Empty crop region from bbox {bbox} on {width}x{height} image")

        cropped = img.crop((left, top, right, bottom))

        output = io.BytesIO()
        cropped.save(output, format=fmt)
        result = output.getvalue()

        logger.info(
            "Cropped image to document ROI",
            extra={"original_size": (width, height), "cropped_size": cropped.size},
        )
        return result

    except Exception as e:
        raise ValueError(f"Image crop failed: {e}") from e


def is_file_too_large_for_bda(content_type: str, file_size_bytes: int) -> bool:
    """Check if file exceeds BDA size limits based on content type."""
    if content_type in ["image/jpeg", "image/png"]:
        return int(file_size_bytes) > int(ConfigDefaults.BDA_MAX_IMAGE_SIZE_BYTES)
    elif content_type in ["application/pdf", "image/tiff"]:
        return int(file_size_bytes) > int(ConfigDefaults.BDA_MAX_DOCUMENT_FILE_SIZE_BYTES)
    else:
        # unknown file type, assume document limit
        return int(file_size_bytes) > int(ConfigDefaults.BDA_MAX_IMAGE_SIZE_BYTES)


def convert_to_grayscale(
    object_key: str, file_bytes: bytes, content_type: str
) -> tuple[bytes, str]:
    """Convert image to grayscale, and to PDF if over 5MB."""
    if content_type not in FileValidation.GRAYSCALE_CONVERTIBLE:
        return file_bytes, content_type

    try:
        img = Image.open(io.BytesIO(file_bytes))
        gray = img.convert("L")

        # try jpeg first
        jpeg_output = io.BytesIO()
        gray.save(jpeg_output, format="JPEG", quality=100)
        jpeg_bytes = jpeg_output.getvalue()

        if len(jpeg_bytes) > int(ConfigDefaults.BDA_MAX_IMAGE_SIZE_BYTES):
            logger.info(f"{object_key} too large for BDA, converting to PDF")
            pdf_output = io.BytesIO()
            gray.save(pdf_output, format="PDF")
            return pdf_output.getvalue(), "application/pdf"
        else:
            return jpeg_bytes, "image/jpeg"

    except Exception as e:
        logger.error(f"Grayscale conversion failed: {e}")
        return file_bytes, content_type


def optimize_s3_image(
    bucket_name: str,
    object_key: str,
    *,
    apply_grayscale: bool = False,
) -> OptimizationResult:
    """Crop and/or grayscale-convert an S3 image in a single download/upload pass.

    Performs both transforms in memory and writes the final result to S3 once,
    eliminating the redundant GET+PUT that occurred when crop and grayscale were
    invoked separately.

    Args:
        bucket_name: S3 bucket containing the image.
        object_key: S3 object key.
        apply_grayscale: Whether to apply grayscale conversion.

    Returns:
        OptimizationResult with crop metadata, grayscale flag, and final size.
    """
    result = OptimizationResult(crop_result=CropResult())

    try:
        response = s3_service.get_object(bucket_name, object_key)
        file_bytes = response["Body"].read()
        content_type = response.get("ContentType", "application/octet-stream")
    except Exception as e:
        logger.error(f"Failed to download {object_key}: {e}")
        result.failed = True
        return result

    modified = False

    # --- Crop (best-effort: any failure leaves bytes untouched) ---
    if is_document_crop_enabled() and content_type.startswith("image/"):
        try:
            bbox, crop_result = detect_document_bbox(file_bytes, content_type)
            result.crop_result = crop_result

            if bbox is not None:
                cropped_bytes = crop_image_to_bbox(file_bytes, bbox)
                file_bytes = cropped_bytes
                modified = True

                x1, y1, x2, y2 = bbox
                retained = Decimal(str(round((x2 - x1) * (y2 - y1) / 1_000_000 * 100, 2)))
                crop_result.cropped = True
                crop_result.bounding_box = bbox
                crop_result.retained_percentage = retained
                logger.info(f"Cropped {object_key} to document ROI (retained {retained}%)")
            else:
                logger.info(f"No document ROI detected for {object_key}; skipping crop")
        except Exception as e:
            logger.warning(f"Document ROI crop skipped for {object_key}: {e}")

    # --- Grayscale ---
    if apply_grayscale:
        converted_bytes, converted_type = convert_to_grayscale(object_key, file_bytes, content_type)
        # convert_to_grayscale returns the same object when content_type is not
        # convertible or on error; identity check detects actual conversion.
        if converted_bytes is not file_bytes:
            file_bytes = converted_bytes
            content_type = converted_type
            result.grayscale_applied = True
            modified = True

    # --- Single write ---
    if modified:
        s3_service.put_object(bucket_name, object_key, file_bytes, content_type)

    result.file_size_bytes = len(file_bytes)
    result.too_large = is_file_too_large_for_bda(content_type, len(file_bytes))

    if result.too_large:
        logger.error(f"File still too large after optimization: {len(file_bytes)} bytes")
    else:
        logger.info(f"Optimized {object_key} for BDA processing ({len(file_bytes)} bytes)")

    return result
