"""Prepare an uploaded S3 image for Bedrock Data Automation.

These helpers download an S3 object, transform it (crop to the document ROI,
grayscale, downsize), and overwrite it in place before BDA is invoked. They are
best-effort: a failure leaves the original object untouched so BDA still runs.
"""

import io
import os

from PIL import Image

from documentai_api.config.constants import ConfigDefaults, FileValidation
from documentai_api.config.env import EnvVars
from documentai_api.logging import get_logger
from documentai_api.services import s3 as s3_service
from documentai_api.utils.bedrock import detect_document_bbox
from documentai_api.utils.s3 import parse_s3_uri
from documentai_api.utils.ssm import is_document_crop_enabled

logger = get_logger(__name__)


def _save_precrop_original(object_key: str, file_bytes: bytes, content_type: str) -> None:
    """Save the pre-crop image to the preprocessing location for audit/recovery.

    Stored under a ``precrop/`` sub-prefix so it never collides with the upload-time
    original audit copy. Raises if no preprocessing location is configured or the
    save fails - the caller must abort the crop rather than overwrite the original
    with no recoverable backup.
    """
    location = os.environ.get(EnvVars.DOCUMENTAI_PREPROCESSING_LOCATION)
    if not location:
        raise RuntimeError(
            "DOCUMENTAI_PREPROCESSING_LOCATION is not set; refusing to crop without "
            "a pre-crop backup of the original"
        )

    pre_bucket, pre_prefix = parse_s3_uri(location)
    base = os.path.basename(object_key)
    pre_key = f"{pre_prefix}/precrop/{base}" if pre_prefix else f"precrop/{base}"

    s3_service.put_object(pre_bucket, pre_key, file_bytes, content_type)
    logger.info(f"Saved pre-crop original to preprocessing: {pre_key}")


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


def convert_s3_object_to_grayscale(bucket_name: str, object_key: str) -> bool:
    """Convert S3 image to grayscale in-place."""
    try:
        # download file
        response = s3_service.get_object(bucket_name, object_key)
        file_bytes = response["Body"].read()
        content_type = response.get("ContentType", "application/octet-stream")

        # convert to grayscale
        grayscale_bytes, content_type = convert_to_grayscale(object_key, file_bytes, content_type)

        # upload back (overwrite)
        s3_service.put_object(bucket_name, object_key, grayscale_bytes, content_type)

        # Check final size
        final_size = len(grayscale_bytes)
        if is_file_too_large_for_bda(content_type, final_size):
            logger.error(f"File still too large after conversion: {final_size} bytes")
            return False

        logger.info(f"Converted {object_key} for BDA processing")

        return True
    except Exception as e:
        logger.error(f"Failed to convert {object_key} to grayscale: {e}")
        return False


def crop_image_to_document_roi(bucket_name: str, object_key: str) -> None:
    """Crop an S3 image in-place to the document's region of interest before BDA.

    Uses the Bedrock vision model to locate the document, then crops with PIL and
    overwrites the S3 object. Best-effort and feature-flag gated: any miss (flag
    off, non-image, no document found, or error) leaves the object untouched so
    BDA still runs on the full image.
    """
    if not is_document_crop_enabled():
        return

    try:
        response = s3_service.get_object(bucket_name, object_key)
        file_bytes = response["Body"].read()
        content_type = response.get("ContentType", "application/octet-stream")

        if not content_type.startswith("image/"):
            return

        bbox = detect_document_bbox(file_bytes, content_type)
        if bbox is None:
            logger.info(f"No document ROI detected for {object_key}; leaving image uncropped")
            return

        cropped_bytes = crop_image_to_bbox(file_bytes, bbox)
        # preserve the pre-crop image first; if the backup can't be made, the
        # exception aborts the crop so we never overwrite the original unrecoverably
        _save_precrop_original(object_key, file_bytes, content_type)
        s3_service.put_object(bucket_name, object_key, cropped_bytes, content_type)
        logger.info(f"Cropped {object_key} to document ROI before BDA")
    except Exception as e:
        # never block processing on a crop failure
        logger.warning(f"Document ROI crop skipped for {object_key}: {e}")
