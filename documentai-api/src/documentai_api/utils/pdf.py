"""PDF and document manipulation utilities."""

import io
from typing import Any

import pypdfium2 as pdfium
from PIL import Image
from pypdf import PdfReader, PdfWriter

from documentai_api.constants.defaults import SystemDefaults
from documentai_api.constants.file_validation import FileValidation
from documentai_api.dtos.processing import PageMetadata
from documentai_api.logging import get_logger
from documentai_api.services import s3 as s3_service

# Limit maximum image pixels to prevent pixel-flood DoS.
Image.MAX_IMAGE_PIXELS = SystemDefaults.MAX_IMAGE_PIXELS

logger = get_logger(__name__)


def merge_pages_to_pdf(pages: list[PageMetadata]) -> io.BytesIO:
    """Merge multiple pages (PDF/images) from S3 into single PDF.

    Args:
        pages: List of PageMetadata objects with 's3Key', 's3BucketName', and 'pageNumber' fields

    Returns:
        Merged PDF as a seeked BytesIO stream

    Raises:
        ValueError: If unsupported file type encountered
    """
    writer = PdfWriter()

    # sort pages by page number
    sorted_pages = sorted(pages, key=lambda p: p.page_number)

    for page in sorted_pages:
        s3_key = page.s3_key
        logger.info(f"Processing page {page.page_number}: {s3_key}")

        # download file from S3
        file_bytes = s3_service.get_file_bytes(page.s3_bucket_name, s3_key)

        # determine file type from content, not extension
        if FileValidation.is_pdf(file_bytes):
            _add_pdf_pages(writer, file_bytes)
        elif FileValidation.is_image(file_bytes):
            _add_image_as_pdf_page(writer, file_bytes)
        else:
            raise ValueError(f"Unsupported file content for page {page.page_number}")

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output


def get_pdf_page_count(pdf_bytes: bytes) -> int:
    try:
        return len(PdfReader(io.BytesIO(pdf_bytes)).pages)
    except Exception as e:
        logger.warning(f"Error getting PDF page count: {e}")
        return 1


def _chunk_pdf(pdf_bytes: bytes, chunk_size: int, stop_after_first: bool = False) -> list[bytes]:
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        total = len(reader.pages)

        if total <= chunk_size:
            return [pdf_bytes]

        chunks = []
        for start in range(0, total, chunk_size):
            writer = PdfWriter()
            for page in reader.pages[start : start + chunk_size]:
                writer.add_page(page)
            out = io.BytesIO()
            writer.write(out)
            chunks.append(out.getvalue())

            if stop_after_first:
                return chunks

        return chunks
    except Exception as e:
        logger.warning(f"PDF chunking failed, using original bytes: {e}")
        return [pdf_bytes]


def chunk_pdf(pdf_bytes: bytes, chunk_size: int) -> list[bytes]:
    """Split a PDF into chunks of *chunk_size* pages, returning each as bytes.

    Returns a list with the original bytes as the sole element if the PDF has
    fewer pages than *chunk_size* or cannot be parsed.
    """
    return _chunk_pdf(pdf_bytes, chunk_size)


def _is_oversized(obj: Any, limit: int) -> bool:
    return max(int(obj.get("/Width", 0)), int(obj.get("/Height", 0))) > limit


def _has_oversized_image(reader: PdfReader, max_dimension_px: int) -> bool:
    """Cheap read-only scan of image XObject dimensions; never decodes image data."""
    for page in reader.pages:
        resources = page.get("/Resources")
        xobjects = resources.get_object().get("/XObject") if resources else None
        if not xobjects:
            continue

        for ref in xobjects.get_object().values():
            obj = ref.get_object()
            if obj.get("/Subtype") == "/Image" and _is_oversized(obj, max_dimension_px):
                return True
    return False


def _flatten_pdf_with_pdfium(pdf_bytes: bytes, max_dimension_px: int) -> bytes:
    """Render every page as a JPEG bitmap at a scale that fits the long side within *max_dimension_px*.

    Text layer is not preserved.
    """
    doc = pdfium.PdfDocument(pdf_bytes)
    writer = PdfWriter()
    for i in range(len(doc)):
        page = doc[i]
        w, h = page.get_size()
        if max(w, h) == 0:
            raise ValueError(f"Page {i} has zero size")

        scale = max_dimension_px / max(w, h)
        bitmap = page.render(scale=scale)
        img = bitmap.to_pil()
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        buf = io.BytesIO()
        img.save(buf, format="PDF", quality=85)
        _add_pdf_pages(writer, buf.getvalue())
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def compress_pdf_for_classification(pdf_bytes: bytes, max_dimension_px: int) -> bytes:
    """Return a copy of the PDF with every page rasterized at *max_dimension_px* on the long side.

    A read-only pre-scan of image XObject dimensions returns the original bytes
    immediately when no image exceeds *max_dimension_px*, skipping all work for
    digital PDFs and small scans.  When any image is oversized, every page is
    rendered to a JPEG bitmap via pypdfium2 and reassembled into a new PDF.
    Text layer is not preserved in the output; BDA receives the original bytes.

    Falls back to the original bytes on any error so callers always get a usable PDF.
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        if not _has_oversized_image(reader, max_dimension_px):
            return pdf_bytes

        compressed = _flatten_pdf_with_pdfium(pdf_bytes, max_dimension_px)
        if len(compressed) >= len(pdf_bytes):
            return pdf_bytes
        logger.info(
            f"Compressed PDF for classification: {len(pdf_bytes):,} -> {len(compressed):,} bytes"
        )
        return compressed

    except Exception as e:
        logger.warning(f"PDF compression for classification failed, using original: {e}")
        return pdf_bytes


def truncate_pdf_to_pages(pdf_bytes: bytes, max_pages: int) -> bytes:
    """Return a new PDF containing only the first *max_pages* pages."""
    return _chunk_pdf(pdf_bytes, max_pages, stop_after_first=True)[0]


def _add_pdf_pages(writer: PdfWriter, pdf_bytes: bytes) -> None:
    """Add all pages from a PDF to the writer."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    for page in reader.pages:
        writer.add_page(page)


def _add_image_as_pdf_page(writer: PdfWriter, image_bytes: bytes) -> None:
    """Convert image to PDF page and add to writer."""
    image = Image.open(io.BytesIO(image_bytes))

    # convert to rgb if needed (handles png transparency, etc.)
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    # create pdf from image
    img_pdf_bytes = io.BytesIO()
    image.save(img_pdf_bytes, format="PDF")
    img_pdf_bytes.seek(0)

    # add to merged pdf
    reader = PdfReader(img_pdf_bytes)
    for page in reader.pages:
        writer.add_page(page)
