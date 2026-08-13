"""File format conversion for images (HEIC, WebP, GIF, BMP, TIFF)."""

import io

from PIL import Image

from documentai_api.logging import get_logger

logger = get_logger(__name__)


def convert_image_to_png(file_bytes: bytes, content_type: str) -> bytes:
    """Convert HEIC/WebP/GIF/BMP/TIFF image bytes to PNG.

    For animated GIFs, extracts the first frame only.

    Raises:
        ValueError: If conversion fails.
    """
    try:
        if content_type in ("image/heic", "image/heif"):
            from pillow_heif import register_heif_opener  # type: ignore[import-untyped]

            register_heif_opener()

        img = Image.open(io.BytesIO(file_bytes))

        if content_type == "image/gif" and getattr(img, "is_animated", False):
            img.seek(0)

        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        output = io.BytesIO()
        img.save(output, format="PNG")
        result = output.getvalue()

        logger.info(
            f"Converted {content_type} to PNG",
            extra={"original_size": len(file_bytes), "converted_size": len(result)},
        )

        return result

    except Exception as e:
        raise ValueError(f"Image conversion failed for {content_type}: {e}") from e


def convert_file(file_bytes: bytes, content_type: str) -> tuple[bytes, str]:
    """Convert a file to a BDA-native format.

    Returns:
        Tuple of (converted_bytes, output_content_type).

    Raises:
        ValueError: If conversion fails or content type is not supported.
    """
    image_types = (
        "image/bmp",
        "image/heic",
        "image/heif",
        "image/webp",
        "image/gif",
        "image/tiff",
    )
    if content_type in image_types:
        return convert_image_to_png(file_bytes, content_type), "image/png"

    raise ValueError(f"No conversion available for {content_type}")
