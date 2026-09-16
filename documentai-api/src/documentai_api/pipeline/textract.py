"""Textract pipeline: calls extractor, processor, and classifier. Returns bool (handled)."""

from documentai_api.classifiers.document_classification import classify_extraction_result
from documentai_api.config.constants import ExtractMethod
from documentai_api.extractors.textract import extract_textract_identity
from documentai_api.logging import get_logger
from documentai_api.processors.textract import process_textract_result

logger = get_logger(__name__)


def run_textract_pipeline(
    ddb_key: str,
    content_type: str,
    file_bytes: bytes,
    tenant_id: str,
    batch_id: str | None = None,
) -> bool:
    """Run Textract identity extraction, write output, and classify.

    Returns True if Textract handled the document, False to fall through to BDA.
    """
    result = extract_textract_identity(content_type, file_bytes, ddb_key)

    if result is None:
        return False

    processor_result = process_textract_result(ddb_key, result, tenant_id, batch_id)

    if processor_result.extraction_result is None:
        return False

    classify_extraction_result(
        ddb_key=processor_result.object_key,
        result=processor_result.extraction_result,
        output_uri=processor_result.output_uri,
        tenant_id=processor_result.tenant_id,
        batch_id=processor_result.batch_id,
        extraction_method=ExtractMethod.TEXTRACT,
    )

    return True
