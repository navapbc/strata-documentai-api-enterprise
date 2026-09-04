"""Dispatch to the appropriate reader based on extract method."""

import json
from typing import Any

from documentai_api.config.constants import ExtractMethod
from documentai_api.readers.bda import extract_field_values_from_bda_results
from documentai_api.readers.textract import extract_field_values_from_textract_results
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.bda import get_bda_result_json


def read_extraction_fields(
    ddb_record: dict[str, Any],
    include_extracted_data: bool,
    include_bounding_box: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Fetch stored extraction result from S3 and dispatch to the appropriate reader.

    Returns (field_confidence_map_list, field_values, field_geometry).
    """
    if not include_extracted_data:
        field_confidence_map_list = json.loads(
            ddb_record.get(DocumentMetadata.FIELD_CONFIDENCE_SCORES, "[]")
        )
        return field_confidence_map_list, {}, {}

    s3_uri = ddb_record.get(DocumentMetadata.BDA_OUTPUT_S3_URI)
    if not s3_uri:
        return [], {}, {}

    bda_results = get_bda_result_json(s3_uri)
    if not bda_results:
        return [], {}, {}

    extract_method = ddb_record.get(DocumentMetadata.EXTRACT_METHOD)

    if extract_method == ExtractMethod.TEXTRACT:
        metadata, field_values, field_geometry = extract_field_values_from_textract_results(
            bda_results
        )
        return metadata["field_confidence_map_list"], field_values, field_geometry

    metadata, field_values, field_geometry = extract_field_values_from_bda_results(
        bda_results, include_geometry=include_bounding_box
    )
    return metadata.field_confidence_map_list, field_values, field_geometry
