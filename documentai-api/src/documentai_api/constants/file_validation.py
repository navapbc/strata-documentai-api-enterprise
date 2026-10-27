from collections.abc import Iterable
from typing import ClassVar

import filetype  # type: ignore[import-untyped]


class FileValidation:
    # === Office document MIME types ===
    PDF_MIME = "application/pdf"
    DOC_MIME = "application/msword"
    DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

    # === Office container detection ===
    # ZIP local-file-header magic (all OOXML: docx/xlsx/pptx). OLE2/Compound File
    # magic covers legacy .doc/.xls AND ECMA-376-encrypted OOXML.
    ZIP_MAGIC = b"PK\x03\x04"
    OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

    # OOXML archive member prefix -> MIME. filetype only scans the first ~6KB of
    # the archive for this entry, so it misses it in newer Office layouts;
    # detect_ooxml_mime inspects the full member list instead.
    OOXML_MEMBER_MIME: ClassVar[tuple[tuple[str, str], ...]] = (
        ("word/", DOCX_MIME),
        ("xl/", XLSX_MIME),
        ("ppt/", PPTX_MIME),
    )

    # OLE2 stores stream names as UTF-16LE. An ECMA-376-encrypted OOXML package
    # carries these two streams; presence identifies a password-protected doc.
    OOXML_ENCRYPTION_MARKERS: ClassVar[tuple[bytes, ...]] = (
        "EncryptionInfo".encode("utf-16-le"),
        "EncryptedPackage".encode("utf-16-le"),
    )

    @staticmethod
    def is_office_container_magic(data: bytes) -> bool:
        """True if bytes start with a ZIP or OLE2 signature.

        These container formats (OOXML, and legacy/encrypted Office docs) can't be
        identified from a header alone - the caller must read the full file for
        detect_ooxml_mime / has_ooxml_encryption_markers to work. Everything else
        is a simple magic-number format that a header probe resolves.
        """
        return data.startswith((FileValidation.ZIP_MAGIC, FileValidation.OLE2_MAGIC))

    @staticmethod
    def detect_ooxml_mime(member_names: Iterable[str]) -> str | None:
        """Map an OOXML archive's member names to its MIME type, or None if not OOXML."""
        names = list(member_names)
        for prefix, mime in FileValidation.OOXML_MEMBER_MIME:
            if any(name.startswith(prefix) for name in names):
                return mime
        return None

    @staticmethod
    def has_ooxml_encryption_markers(data: bytes) -> bool:
        """True if bytes carry the OLE2 streams of an ECMA-376-encrypted OOXML package."""
        return all(marker in data for marker in FileValidation.OOXML_ENCRYPTION_MARKERS)

    NO_CONVERSION_NEEDED = (
        PDF_MIME,
        DOC_MIME,
        DOCX_MIME,
        "image/jpeg",
        "image/png",
    )

    REQUIRES_CONVERSION = (
        "image/bmp",
        "image/heic",
        "image/heif",
        "image/webp",
        "image/gif",
        "image/tiff",
    )

    SUPPORTED_CONTENT_TYPES = NO_CONVERSION_NEEDED + REQUIRES_CONVERSION

    PREVIEWABLE_TYPES = (
        "application/pdf",
        "image/jpeg",
        "image/png",
    )

    GRAYSCALE_CONVERTIBLE = (
        "image/jpeg",
        "image/png",
    )

    ODT_CONTENT_TYPES = ("application/vnd.oasis.opendocument.text",)

    @staticmethod
    def is_pdf(data: bytes) -> bool:
        return data[:4] == b"%PDF"

    @staticmethod
    def is_image(data: bytes) -> bool:
        mime = filetype.guess_mime(data)
        return (
            mime is not None
            and mime in FileValidation.SUPPORTED_CONTENT_TYPES
            and mime.startswith("image/")
        )

    @staticmethod
    def is_supported(content_type: str) -> bool:
        return content_type in FileValidation.SUPPORTED_CONTENT_TYPES

    @staticmethod
    def needs_conversion(content_type: str) -> bool:
        return content_type in FileValidation.REQUIRES_CONVERSION

    @staticmethod
    def is_odt(content_type: str) -> bool:
        return content_type in FileValidation.ODT_CONTENT_TYPES

    CONTENT_TYPE_TO_EXT: ClassVar[dict[str, str]] = {
        PDF_MIME: "pdf",
        DOC_MIME: "doc",
        DOCX_MIME: "docx",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/png": "png",
        "image/tiff": "tiff",
        "image/bmp": "bmp",
        "image/heic": "heic",
        "image/heif": "heif",
        "image/webp": "webp",
        "image/gif": "gif",
    }

    @staticmethod
    def get_extension(content_type: str, unknown: str = "bin") -> str:
        ct = content_type.lower().split(";")[0].strip()
        return FileValidation.CONTENT_TYPE_TO_EXT.get(ct, unknown)


class TextractConfig:
    """Textract AnalyzeID configuration."""

    # Content types supported by Textract AnalyzeID (inline bytes)
    SUPPORTED_CONTENT_TYPES = (
        "image/jpeg",
        "image/png",
        "application/pdf",
    )
