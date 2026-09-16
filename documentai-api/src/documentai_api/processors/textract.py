"""Textract processor: resolves tenant context, writes output. Returns ProcessorResult."""

from documentai_api.config.constants import ExtractMethod
from documentai_api.dtos.extraction import ExtractionResult
from documentai_api.dtos.processing import ProcessorResult
from documentai_api.logging import get_logger
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.ddb import get_ddb_record
from documentai_api.utils.s3 import write_extraction_output

logger = get_logger(__name__)


def process_textract_result(
    ddb_key: str,
    result: ExtractionResult,
    tenant_id: str | None = None,
    batch_id: str | None = None,
) -> ProcessorResult:
    """Resolve tenant context, write tenant-scoped output, return ProcessorResult."""
    tenant_id = tenant_id or (get_ddb_record(ddb_key) or {}).get(DocumentMetadata.TENANT_ID)
    output_uri: str | None = None

    if tenant_id:
        output_uri = write_extraction_output(
            tenant_id,
            ExtractMethod.TEXTRACT,
            ddb_key,
            result.body or b"",
            content_type="application/json",
        )

    return ProcessorResult(
        object_key=ddb_key,
        tenant_id=tenant_id,
        batch_id=batch_id,
        extraction_result=result,
        output_uri=output_uri,
    )
