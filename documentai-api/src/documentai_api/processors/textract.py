"""Textract processor: DDB finalization and classification dispatch."""

from documentai_api.dtos.extraction import ExtractionResult
from documentai_api.logging import get_logger

logger = get_logger(__name__)


def process_textract_result(
    ddb_key: str,
    result: ExtractionResult,
    user_provided_document_category: str | None,
    batch_id: str | None = None,
) -> None:
    """Update the DDB record with Textract extraction results."""
    from documentai_api.schemas.document_metadata import DocumentMetadata
    from documentai_api.utils.ddb import get_ddb_record
    from documentai_api.utils.document_classification import classify_extraction_result

    tenant_id = (get_ddb_record(ddb_key) or {}).get(DocumentMetadata.TENANT_ID)
    classify_extraction_result(ddb_key, result, tenant_id, batch_id)
