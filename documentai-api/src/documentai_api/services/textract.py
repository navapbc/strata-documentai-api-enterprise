"""Textract AnalyzeID service for identity documents (driver's licenses, passports)."""

from typing import Any

from documentai_api.logging import get_logger
from documentai_api.services.aws_client_factory import AWSClientFactory

logger = get_logger(__name__)


def analyze_id(image_bytes: bytes) -> dict[str, Any]:
    """Call Textract AnalyzeID for identity documents."""
    logger.info(f"Calling Textract AnalyzeID ({len(image_bytes)} bytes)")
    try:
        client = AWSClientFactory.get_textract_client()
        response: dict[str, Any] = client.analyze_id(DocumentPages=[{"Bytes": image_bytes}])
        doc_count = len(response.get("IdentityDocuments", []))
        logger.info(f"Textract AnalyzeID returned {doc_count} identity document(s)")
        return response
    except Exception as e:
        logger.error(f"Textract AnalyzeID failed: {e}")
        raise


def _detect_document_text(image_bytes: bytes) -> list[dict[str, Any]]:
    """Call Textract DetectDocumentText and return the raw Blocks list."""
    client = AWSClientFactory.get_textract_client()
    response: dict[str, Any] = client.detect_document_text(Document={"Bytes": image_bytes})
    blocks: list[dict[str, Any]] = response["Blocks"]
    return blocks


def get_words(image_bytes: bytes) -> list[dict[str, Any]]:
    """Return WORD blocks from Textract DetectDocumentText."""
    return [b for b in _detect_document_text(image_bytes) if b["BlockType"] == "WORD"]


def get_ocr_blocks(image_bytes: bytes) -> list[dict[str, Any]]:
    """Return all blocks from Textract DetectDocumentText (LINE, WORD, PAGE, etc.)."""
    return _detect_document_text(image_bytes)


def get_layout_ocr_blocks(image_bytes: bytes) -> list[dict[str, Any]]:
    """Return all blocks from Textract AnalyzeDocument with the LAYOUT feature.

    Includes the same LINE/WORD/PAGE blocks as DetectDocumentText, plus LAYOUT_*
    blocks (LAYOUT_TEXT, LAYOUT_TABLE, etc.) whose CHILD relationships reference
    LINE blocks in correct multi-column reading order. Used for the LLM
    extraction path only - DetectDocumentText's flat line order can interleave
    side-by-side columns (e.g. a letterhead address next to an employee info
    block), which confuses citation-based extraction.
    """
    client = AWSClientFactory.get_textract_client()
    response: dict[str, Any] = client.analyze_document(
        Document={"Bytes": image_bytes}, FeatureTypes=["LAYOUT"]
    )
    blocks: list[dict[str, Any]] = response["Blocks"]
    return blocks
