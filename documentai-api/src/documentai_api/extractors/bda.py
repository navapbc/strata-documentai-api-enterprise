"""BDA extractor: extract fields from a BDA result into an ExtractionResult."""

from typing import Any

from documentai_api.config.constants import BdaResponseFields
from documentai_api.dtos.extraction import ExtractionResult
from documentai_api.readers.bda import extract_field_values_from_bda_results
from documentai_api.utils.bda import get_matched_blueprint


def extract_bda_result(
    bda_result_json: dict[str, Any],
    bda_output_s3_uri: str,
) -> ExtractionResult | None:
    """Extract fields from a matched BDA blueprint. Returns None if no blueprint matched."""
    matched_blueprint = get_matched_blueprint(bda_result_json)
    if matched_blueprint.name is None:
        return None

    document_class = bda_result_json.get(BdaResponseFields.DOCUMENT_CLASS, {}).get(
        BdaResponseFields.DOCUMENT_TYPE
    )

    metadata, _, _ = extract_field_values_from_bda_results(bda_result_json)

    return ExtractionResult(
        document_type=document_class,
        output_s3_uri=bda_output_s3_uri,
        field_confidence_scores=metadata.field_confidence_map_list,
        field_empty_list=metadata.empty_fields,
        field_missing_geometry_list=metadata.fields_missing_geometry or [],
        matched_blueprint_name=matched_blueprint.name,
        matched_blueprint_confidence=matched_blueprint.confidence,
    )
