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
