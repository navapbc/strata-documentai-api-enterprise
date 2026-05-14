"""Lightweight document utilities. No CV dependencies."""

import io

from documentai_api.config.constants import ConfigDefaults
from documentai_api.logging import get_logger

logger = get_logger(__name__)


def _get_pdf_page_count(file_bytes: bytes) -> int:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        return len(reader.pages)
    except Exception as e:
        logger.warning(f"Error getting PDF page count: {e}")
        return 1


def _get_tiff_page_count(file_bytes: bytes) -> int:
    from PIL import Image

    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            page_count = 0
            while True:
                try:
                    img.seek(page_count)
                    page_count += 1
                except EOFError:
                    break
            return page_count
    except Exception as e:
        logger.warning(f"Error getting TIFF page count: {e}")
        return 1


def detect_file_type(file_bytes: bytes) -> str:
    """Detect file type from binary header bytes."""
    if not file_bytes:
        return "Unknown"

    if file_bytes.startswith(b"\xff\xd8"):
        return "JPEG"
    elif file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    elif file_bytes.startswith(b"GIF87a") or file_bytes.startswith(b"GIF89a"):
        return "GIF"
    elif file_bytes.startswith(b"%PDF"):
        return "PDF"
    elif file_bytes.startswith(b"\x49\x49\x2a\x00") or file_bytes.startswith(b"\x4d\x4d\x00\x2a"):
        return "TIFF"
    elif file_bytes.startswith(b"BM"):
        return "BMP"
    return "Unknown"


def is_password_protected(file_bytes: bytes) -> bool:
    """Detect if PDF is password protected."""
    if detect_file_type(file_bytes) == "PDF":
        return b"/Encrypt" in file_bytes[:4096]
    return False


def get_page_count(file_bytes: bytes) -> int | None:
    """Count total pages in document."""
    if not file_bytes:
        return None

    file_type = detect_file_type(file_bytes)

    if file_type == "PDF":
        return _get_pdf_page_count(file_bytes)
    elif file_type == "TIFF":
        return _get_tiff_page_count(file_bytes)
    return 1


def _truncate_pdf(file_bytes: bytes, max_pages: int) -> bytes:
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(io.BytesIO(file_bytes))
    if len(reader.pages) <= max_pages:
        return file_bytes

    writer = PdfWriter()
    for i in range(min(max_pages, len(reader.pages))):
        writer.add_page(reader.pages[i])

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _truncate_tiff(file_bytes: bytes, max_pages: int) -> bytes:
    """Extract first N frames from TIFF and return as new TIFF bytes."""
    from PIL import Image

    tiff_bytes = io.BytesIO(file_bytes)
    output_bytes = io.BytesIO()

    with Image.open(tiff_bytes) as tiff:
        # get total frames
        total_frames = tiff.n_frames  # type: ignore[attr-defined]
        frames_to_process = min(total_frames, max_pages)

        # extract first N frames
        frames = []
        for i in range(frames_to_process):
            tiff.seek(i)
            frame = tiff.copy()
            frames.append(frame)

        # save as new multi-frame TIFF
        if frames:
            frames[0].save(
                output_bytes,
                format="TIFF",
                save_all=True,
                append_images=frames[1:] if len(frames) > 1 else [],
            )

    return output_bytes.getvalue()


def truncate_to_pages(
    file_bytes: bytes, max_pages: int = int(ConfigDefaults.MAX_PAGES_PER_DOCUMENT)
) -> bytes:
    file_type = detect_file_type(file_bytes)

    if file_type == "PDF":
        return _truncate_pdf(file_bytes, max_pages)
    elif file_type == "TIFF":
        return _truncate_tiff(file_bytes, max_pages)
    else:
        return file_bytes
