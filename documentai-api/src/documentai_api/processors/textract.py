"""Textract processor: resolves tenant context. Returns ProcessorResult."""

from documentai_api.dtos.extraction import ExtractionResult
from documentai_api.dtos.processing import ProcessorResult
from documentai_api.logging import get_logger
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.ddb import get_ddb_record

logger = get_logger(__name__)


def process_textract_result(
    ddb_key: str,
    result: ExtractionResult,
    batch_id: str | None = None,
) -> ProcessorResult:
    """Resolve tenant context and return ProcessorResult for pipeline classification."""
    tenant_id = (get_ddb_record(ddb_key) or {}).get(DocumentMetadata.TENANT_ID)
    return ProcessorResult(
        object_key=ddb_key,
        tenant_id=tenant_id,
        batch_id=batch_id,
        extraction_result=result,
    )
