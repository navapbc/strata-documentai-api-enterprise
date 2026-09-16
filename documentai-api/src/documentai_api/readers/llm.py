"""LLM reader: extract field values from stored LLM extraction result JSON."""

from typing import Any

from documentai_api.dtos.processing import ReaderResult


def read_llm_output(
    result_json: dict[str, Any],
    include_geometry: bool = False,
) -> ReaderResult:
    """Extract field confidence metadata, values, and geometry from stored LLM results."""
    fields = result_json.get("fields", {})

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

        field_values[name] = value

        if "geometry" in data and include_geometry:
            field_geometry[name] = {
                "geometry": data["geometry"],
                "type": data.get("fieldType", "string"),
            }

    return ReaderResult(
        field_confidence_map_list=field_confidence_map_list,
        field_values=field_values,
        field_geometry=field_geometry,
        empty_fields=empty_fields,
    )
