"""Dispatch to the appropriate reader based on extract method."""

import json
from typing import Any

from documentai_api.config.constants import ExtractMethod
from documentai_api.dtos.processing import ReaderResult
from documentai_api.readers.bda import read_bda_output
from documentai_api.readers.llm import read_llm_output
from documentai_api.readers.textract import read_textract_output
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.bda import get_bda_result_json

_READERS: dict[str, Any] = {
    ExtractMethod.TEXTRACT: read_textract_output,
    ExtractMethod.BDA: read_bda_output,
    ExtractMethod.LLM: read_llm_output,
}


def read_output(
    ddb_record: dict[str, Any],
    include_extracted_data: bool,
    include_bounding_box: bool = False,
    output_uri: str | None = None,
    extract_method: str | None = None,
) -> ReaderResult:
    """Fetch stored extraction result from S3 and dispatch to the appropriate reader."""
    if not include_extracted_data:
        field_confidence_map_list = json.loads(
            ddb_record.get(DocumentMetadata.FIELD_CONFIDENCE_SCORES, "[]")
        )
        return ReaderResult(
            field_confidence_map_list=field_confidence_map_list, field_values={}, field_geometry={}
        )

    s3_uri = output_uri or ddb_record.get(DocumentMetadata.BDA_OUTPUT_S3_URI)
    if not s3_uri:
        return ReaderResult.empty()

    raw = get_bda_result_json(s3_uri)
    if not raw:
        return ReaderResult.empty()

    method = extract_method or ddb_record.get(DocumentMetadata.EXTRACT_METHOD, ExtractMethod.BDA)
    reader: Any = _READERS.get(method, read_bda_output)
    result: ReaderResult = reader(raw, include_bounding_box)
    return result
