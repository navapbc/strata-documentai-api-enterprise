"""Prepare an uploaded S3 image for Bedrock Data Automation.

These helpers download an S3 object, transform it (crop to the document ROI,
grayscale, downsize), and overwrite it in place before BDA is invoked. They are
best-effort: a failure leaves the original object untouched so BDA still runs.
"""

import io
import time
from decimal import Decimal

from PIL import Image

from documentai_api.config.constants import ConfigDefaults, FileValidation
from documentai_api.dtos.processing import CropResult, OptimizationResult
from documentai_api.logging import get_logger
from documentai_api.services import s3 as s3_service
from documentai_api.utils.bbox_detection import BboxResult, detect_document_bbox
from documentai_api.utils.ssm import is_document_crop_enabled

# Limit maximum image pixels to prevent pixel-flood DoS.
Image.MAX_IMAGE_PIXELS = ConfigDefaults.MAX_IMAGE_PIXELS

logger = get_logger(__name__)


def get_bbox_if_enabled(file_bytes: bytes, content_type: str) -> BboxResult | None:
    """Run bbox detection if the crop feature flag is enabled and content is an image.

    Returns None when crop is disabled or content_type is not an image, so callers
    can treat None as "skip crop" without re-checking the flag.
    """
    if not is_document_crop_enabled() or not content_type.startswith("image/"):
        return None

    return detect_document_bbox(file_bytes, content_type)


def crop_image_to_bbox(
    image_bytes: bytes,
    bbox: tuple[float, float, float, float],
    *,
    pad_ratio: float = 0.03,
    skip_threshold: float = 0.75,
) -> bytes:
    """Crop an image to a bounding box given on a 0-1000 normalized scale.

    The box is rescaled to pixels, padded by ``pad_ratio`` of each dimension (so a
    slightly-loose detection never clips the document), and clamped to the image.
    The output is re-encoded in the source image's format.

    If the bbox already covers more than ``skip_threshold`` of the image area,
    cropping is skipped (returns the original bytes unchanged).

    Raises:
        ValueError: if the image can't be opened or the box is unusable.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        fmt = img.format or "PNG"
        width, height = img.size

        x1, y1, x2, y2 = bbox

        # Skip crop if document already fills most of the frame
        bbox_area = (x2 - x1) * (y2 - y1)
        # bbox coords are on a 0-1000 normalized scale (from Nova bbox detection).
        # Total image area in this coordinate space is 1000 * 1000.
        image_area = 1000.0 * 1000.0
        if bbox_area / image_area >= skip_threshold:
            logger.info(
                "Skipping crop - document covers %.0f%% of frame", bbox_area / image_area * 100
            )
            return image_bytes

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
    file_bytes: bytes | None = None,
    content_type: str | None = None,
    precomputed_bbox: BboxResult | None = None,
) -> OptimizationResult:
    """Crop and/or grayscale-convert an S3 image in a single download/upload pass.

    Performs both transforms in memory and writes the final result to S3 once,
    eliminating the redundant GET+PUT that occurred when crop and grayscale were
    invoked separately.

    Args:
        bucket_name: S3 bucket containing the image.
        object_key: S3 object key.
        apply_grayscale: Whether to apply grayscale conversion.
        file_bytes: Pre-fetched file bytes. If provided, skips the internal GET.
        content_type: Content type corresponding to file_bytes. Required when
            file_bytes is provided.

    Returns:
        OptimizationResult with crop metadata, grayscale flag, and final size.
    """
    result = OptimizationResult(crop_result=CropResult())

    if file_bytes is not None:
        content_type = content_type or "application/octet-stream"
    else:
        try:
            response = s3_service.get_object(bucket_name, object_key)
            file_bytes = response["Body"].read()
            content_type = response.get("ContentType", "application/octet-stream")
        except Exception as e:
            logger.error(f"Failed to download {object_key}: {e}")
            result.failed = True
            return result

    modified = False
    t1 = time.monotonic()

    # --- Crop (best-effort: any failure leaves bytes untouched) ---
    if content_type.startswith("image/"):
        try:
            bbox_result = precomputed_bbox or get_bbox_if_enabled(file_bytes, content_type)
            if bbox_result is not None:
                result.crop_result = bbox_result.crop_result
                if bbox_result.bbox is not None:
                    file_bytes = crop_image_to_bbox(file_bytes, bbox_result.bbox)
                    modified = True
                    x1, y1, x2, y2 = bbox_result.bbox
                    retained = Decimal(str(round((x2 - x1) * (y2 - y1) / 1_000_000 * 100, 2)))
                    bbox_result.crop_result.cropped = True
                    bbox_result.crop_result.bounding_box = bbox_result.bbox
                    bbox_result.crop_result.retained_percentage = retained
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

    result.crop_block_duration_seconds = Decimal(str(round(time.monotonic() - t1, 3)))

    # --- Single write ---
    if modified:
        t2 = time.monotonic()
        s3_service.put_object(bucket_name, object_key, file_bytes, content_type)
        result.write_duration_seconds = Decimal(str(round(time.monotonic() - t2, 3)))

    result.file_size_bytes = len(file_bytes)
    result.too_large = is_file_too_large_for_bda(content_type, len(file_bytes))

    if result.too_large:
        logger.error(f"File still too large after optimization: {len(file_bytes)} bytes")
    else:
        logger.info(f"Optimized {object_key} for BDA processing ({len(file_bytes)} bytes)")

    return result
