"""Tests for utils/zip.py."""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi import HTTPException

from documentai_api.utils.zip import extract_files_from_zip


def _make_zip_upload(zip_bytes: bytes) -> MagicMock:
    mock = MagicMock()
    mock.read = AsyncMock(return_value=zip_bytes)
    mock.filename = "test.zip"
    return mock


@pytest.mark.asyncio
async def test_extract_files_from_zip_success():
    """Test extracting files from ZIP."""
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, "w") as zf:
        zf.writestr("doc1.pdf", b"pdf content 1")
        zf.writestr("doc2.pdf", b"pdf content 2")
    zip_buffer.seek(0)

    mock_zip = MagicMock()
    mock_zip.read = AsyncMock(return_value=zip_buffer.getvalue())

    files = await extract_files_from_zip(mock_zip)

    assert len(files) == 2
    assert files[0].filename == "doc1.pdf"
    assert files[1].filename == "doc2.pdf"
    assert files[0].file.read() == b"pdf content 1"
    files[0].file.seek(0)
    assert files[1].file.read() == b"pdf content 2"


@pytest.mark.asyncio
async def test_extract_files_from_zip_nested_directories():
    """Test extracting files from nested directories in ZIP."""
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, "w") as zf:
        zf.writestr("folder1/doc1.pdf", b"pdf 1")
        zf.writestr("folder1/subfolder/doc2.pdf", b"pdf 2")
        zf.writestr("doc3.pdf", b"pdf 3")
    zip_buffer.seek(0)

    mock_zip = MagicMock()
    mock_zip.read = AsyncMock(return_value=zip_buffer.getvalue())

    files = await extract_files_from_zip(mock_zip)

    assert len(files) == 3
    # should use basename only
    assert files[0].filename == "doc1.pdf"
    assert files[1].filename == "doc2.pdf"
    assert files[2].filename == "doc3.pdf"


@pytest.mark.asyncio
async def test_extract_files_from_zip_skips_directories():
    """Test that directory entries are skipped."""
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, "w") as zf:
        zf.writestr("folder1/", "")  # directory entry
        zf.writestr("folder1/doc1.pdf", b"pdf 1")
    zip_buffer.seek(0)

    mock_zip = MagicMock()
    mock_zip.read = AsyncMock(return_value=zip_buffer.getvalue())

    files = await extract_files_from_zip(mock_zip)

    assert len(files) == 1
    assert files[0].filename == "doc1.pdf"


@pytest.mark.asyncio
async def test_extract_files_from_zip_empty():
    """Test extracting from empty ZIP."""
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, "w"):
        pass  # empty zip
    zip_buffer.seek(0)

    mock_zip = MagicMock()
    mock_zip.read = AsyncMock(return_value=zip_buffer.getvalue())

    files = await extract_files_from_zip(mock_zip)

    assert len(files) == 0


@pytest.mark.asyncio
async def test_zip_bomb_rejected_by_pre_check(monkeypatch):
    from documentai_api.utils import zip as zip_util

    monkeypatch.setattr(zip_util, "MAX_ZIP_EXTRACTED_BYTES", 100)

    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("big.pdf", b"x" * 200)
    zip_buffer.seek(0)

    with pytest.raises(HTTPException, match="exceeds limit"):
        await extract_files_from_zip(_make_zip_upload(zip_buffer.getvalue()))


@pytest.mark.asyncio
async def test_zip_high_ratio_rejected(monkeypatch):
    from documentai_api.utils import zip as zip_util

    monkeypatch.setattr(zip_util, "MAX_ZIP_DECOMPRESSION_RATIO", 2)

    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("big.txt", b"a" * 10_000)
    zip_buffer.seek(0)

    with pytest.raises(HTTPException, match="decompression ratio"):
        await extract_files_from_zip(_make_zip_upload(zip_buffer.getvalue()))
