"""Textract reader: extract field values from stored Textract result JSON."""

from typing import Any


def extract_field_values_from_textract_results(
    result_json: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str], dict[str, dict[str, Any]]]:
    """Extract field confidence metadata, values, and geometry from stored Textract results.

    Returns (metadata_dict, field_values_dict, field_geometry_dict) where metadata_dict has:
      - field_confidence_map_list: list of {name: confidence}
      - empty_fields: list of field names with no value
    """
    fields = result_json.get("fields", {})

    confidence_scores: list[float] = []
    empty_fields: list[str] = []
    field_confidence_map_list: list[dict[str, float]] = []
    field_values: dict[str, str] = {}
    field_geometry: dict[str, dict[str, Any]] = {}

    for name, data in fields.items():
        conf = data["confidence"]
        value = data.get("value", "")

        field_confidence_map_list.append({name: conf})

        if not value:
            empty_fields.append(name)
        else:
            confidence_scores.append(conf)

        field_values[name] = value

        if "geometry" in data:
            field_geometry[name] = {
                "geometry": data["geometry"],
                "type": data.get("fieldType", "string"),
            }

    metadata = {
        "field_confidence_map_list": field_confidence_map_list,
        "empty_fields": empty_fields,
    }
    return metadata, field_values, field_geometry
