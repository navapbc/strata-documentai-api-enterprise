"""BDA reader: extract field values from raw BDA result JSON."""

from typing import Any

from documentai_api.config.constants import BdaResponseFields
from documentai_api.logging import get_logger
from documentai_api.utils.bda import BdaFieldProcessingData, BdaFieldProcessingResult

logger = get_logger(__name__)


def _get_missing_geometry_threshold() -> float:
    from documentai_api.config.constants import ConfigDefaults
    from documentai_api.utils.ssm import is_missing_geo_included_with_missing_fields

    if not is_missing_geo_included_with_missing_fields():
        return 0.0
    return ConfigDefaults.MISSING_GEOMETRY_CONFIDENCE_THRESHOLD


def _process_single_field(field_name: str, field_data: dict[str, Any]) -> BdaFieldProcessingResult:
    confidence = field_data.get(BdaResponseFields.FIELD_CONFIDENCE, 0)
    value = field_data.get(BdaResponseFields.FIELD_VALUE, "")
    is_empty = len(str(value)) == 0
    has_geometry = BdaResponseFields.FIELD_GEOMETRY in field_data

    logger.info(
        f"Extracted field name: {field_name}, confidence: {confidence}, has_geometry: {has_geometry}"
    )

    return BdaFieldProcessingResult(confidence, is_empty, has_geometry)


def _extract_fields_recursive(
    data: dict[str, Any],
    parent_key: str,
    confidence_scores: list[float],
    empty_fields: list[str],
    field_confidence_map_list: list[dict[str, float]],
    fields_missing_geometry: list[str],
    field_values: dict[str, Any] | None = None,
    field_geometry: dict[str, dict[str, Any]] | None = None,
) -> None:
    missing_geo_threshold = _get_missing_geometry_threshold()

    for field_name, field_data in data.items():
        if not isinstance(field_data, dict):
            continue

        full_field_name = f"{parent_key}.{field_name}" if parent_key else field_name

        if (
            BdaResponseFields.FIELD_CONFIDENCE in field_data
            or BdaResponseFields.FIELD_VALUE in field_data
        ):
            field_result = _process_single_field(full_field_name, field_data)
            field_confidence_map_list.append({full_field_name: field_result.confidence})

            if field_result.is_empty:
                empty_fields.append(full_field_name)
            elif not field_result.has_geometry and field_result.confidence < missing_geo_threshold:
                fields_missing_geometry.append(full_field_name)
            else:
                confidence_scores.append(field_result.confidence)

            if field_values is not None:
                field_values[full_field_name] = field_data.get(BdaResponseFields.FIELD_VALUE)

            if field_geometry is not None and BdaResponseFields.FIELD_GEOMETRY in field_data:
                field_geometry[full_field_name] = {
                    "type": field_data.get(BdaResponseFields.FIELD_TYPE),
                    "geometry": field_data[BdaResponseFields.FIELD_GEOMETRY],
                }
        else:
            _extract_fields_recursive(
                field_data,
                full_field_name,
                confidence_scores,
                empty_fields,
                field_confidence_map_list,
                fields_missing_geometry,
                field_values,
                field_geometry,
            )


def extract_field_values_from_bda_results(
    bda_result_json: dict[str, Any],
    include_geometry: bool = False,
) -> tuple[BdaFieldProcessingData, dict[str, Any], dict[str, dict[str, Any]]]:
    """Extract metadata, field values, and optionally geometry from BDA result."""
    if BdaResponseFields.EXPLAINABILITY_INFO not in bda_result_json:
        return (BdaFieldProcessingData([], [], []), {}, {})

    explainability_info = bda_result_json[BdaResponseFields.EXPLAINABILITY_INFO]

    confidence_scores: list[float] = []
    empty_fields: list[str] = []
    field_confidence_map_list: list[dict[str, float]] = []
    fields_missing_geometry: list[str] = []
    field_values: dict[str, Any] = {}
    field_geometry: dict[str, dict[str, Any]] = {}

    for item in explainability_info:
        if isinstance(item, dict):
            _extract_fields_recursive(
                item,
                "",
                confidence_scores,
                empty_fields,
                field_confidence_map_list,
                fields_missing_geometry,
                field_values,
                field_geometry if include_geometry else None,
            )

    metadata = BdaFieldProcessingData(
        confidence_scores=confidence_scores,
        empty_fields=empty_fields,
        field_confidence_map_list=field_confidence_map_list,
        fields_missing_geometry=fields_missing_geometry,
    )

    return (metadata, field_values, field_geometry)
