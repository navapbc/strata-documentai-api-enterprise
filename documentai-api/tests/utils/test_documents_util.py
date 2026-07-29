"""Tests for utils/documents.py detection helpers."""

from pathlib import Path

from documentai_api.utils.documents import is_password_protected

FIXTURES_DIR = Path(__file__).parent.parent / "helpers" / "fixtures" / "test-documents"

# OLE2/Compound File magic shared by legacy .doc/.xls and encrypted OOXML.
_OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def test_is_password_protected_encrypted_ooxml():
    """An ECMA-376-encrypted docx (OLE2-wrapped) is detected as password protected."""
    data = (FIXTURES_DIR / "synthetic-password-protected.docx").read_bytes()
    assert is_password_protected(data) is True


def test_is_password_protected_legacy_doc_not_flagged():
    """A plain legacy .doc shares OLE2 magic but has no encryption streams."""
    doc = bytearray(600)
    doc[0:8] = _OLE2_MAGIC
    doc[512:516] = b"\xec\xa5\xc1\x00"  # Word FIB signature
    assert is_password_protected(bytes(doc)) is False


def test_is_password_protected_encrypted_pdf():
    assert is_password_protected(b"%PDF-1.7\n" + b"/Encrypt 1 0 R\n" + b"0" * 100) is True


def test_is_password_protected_plain_pdf():
    assert is_password_protected(b"%PDF-1.7\n" + b"0" * 100) is False


def test_is_password_protected_non_office_file():
    assert is_password_protected(b"\x89PNG\r\n\x1a\n" + b"0" * 100) is False
