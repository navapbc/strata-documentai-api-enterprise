"""Tests for utils/pdf.py."""

import io
from unittest.mock import patch

from pypdf import PdfReader

from documentai_api.utils.pdf import (
    chunk_pdf,
    compress_pdf_for_classification,
    truncate_pdf_to_pages,
)
from tests.helpers.documents import (
    generate_blank_pdf,
    generate_blank_pdf_image,
    generate_image_pdf_with_text,
)

MAX_PX = 200  # small limit so tests don't need huge images


# --- compress_pdf_for_classification ---


def test_compress_oversized_scan_reduces_size_and_preserves_page_count():
    pdf = generate_blank_pdf_image(num_pages=2, width=2000, height=2000)
    result = compress_pdf_for_classification(pdf, MAX_PX)
    assert len(result) < len(pdf)
    assert len(PdfReader(io.BytesIO(result)).pages) == 2


def test_compress_oversized_page_reduces_size_and_preserves_page_count():
    # pypdfium2 flattens to bitmap; text layer is not preserved
    pdf = generate_image_pdf_with_text("HELLO_MARKER", width=2000, height=2000)
    result = compress_pdf_for_classification(pdf, MAX_PX)
    assert len(result) < len(pdf)
    assert len(PdfReader(io.BytesIO(result)).pages) == 1


def test_compress_digital_pdf_returns_original_object():
    # Blank PDF has no images: pre-scan returns original
    pdf = generate_blank_pdf(num_pages=2)
    result = compress_pdf_for_classification(pdf, MAX_PX)
    assert result is pdf


def test_compress_small_scan_returns_original_object():
    # Images already within limit: any_compressed stays False
    pdf = generate_blank_pdf_image(num_pages=1, width=100, height=100)
    result = compress_pdf_for_classification(pdf, MAX_PX)
    assert result is pdf


def test_compress_malformed_pdf_returns_original_object():
    not_a_pdf = b"%PDF-1.4 not a real pdf"
    result = compress_pdf_for_classification(not_a_pdf, MAX_PX)
    assert result is not_a_pdf


def test_compress_non_pdf_bytes_returns_original_object():
    jpeg = b"\xff\xd8\xff" + b"\x00" * 100
    result = compress_pdf_for_classification(jpeg, MAX_PX)
    assert result is jpeg


def test_compress_size_guard_returns_original_when_flatten_is_larger():
    # If flatten produces a larger file, return the original bytes unchanged
    pdf = generate_blank_pdf_image(num_pages=1, width=201, height=201)
    bloated = pdf + b"\x00" * 100_000
    with patch("documentai_api.utils.pdf._flatten_pdf_with_pdfium", return_value=bloated):
        result = compress_pdf_for_classification(pdf, MAX_PX)
    assert result is pdf


# --- truncate_pdf_to_pages ---


def test_truncate_returns_original_when_under_limit():
    pdf = generate_blank_pdf(num_pages=3)
    result = truncate_pdf_to_pages(pdf, 5)
    assert result is pdf


def test_truncate_cuts_to_max_pages():
    pdf = generate_blank_pdf(num_pages=8)
    result = truncate_pdf_to_pages(pdf, 5)
    assert len(PdfReader(io.BytesIO(result)).pages) == 5


def test_truncate_returns_original_on_malformed_pdf():
    bad_pdf = b"%PDF-1.4 this is not a real pdf"
    result = truncate_pdf_to_pages(bad_pdf, 5)
    assert result is bad_pdf


# --- chunk_pdf ---


def test_chunk_pdf_splits_into_disjoint_windows():
    chunks = chunk_pdf(generate_blank_pdf(num_pages=7), 3)
    assert [len(PdfReader(io.BytesIO(c)).pages) for c in chunks] == [3, 3, 1]


def test_chunk_pdf_at_or_below_window_size_returns_original():
    pdf = generate_blank_pdf(num_pages=3)
    assert chunk_pdf(pdf, 3) == [pdf]
