import re
import uuid as uuid_mod
from dataclasses import dataclass
from typing import Any

from documentai_api.config.constants import (
    UUID_PATTERN,
    BdaResponseFields,
)
from documentai_api.config.env import EnvVars, get_required_env
from documentai_api.logging import get_logger
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.services import ddb as ddb_service

logger = get_logger(__name__)


@dataclass
class BdaFieldProcessingData:
    confidence_scores: list[float]
    empty_fields: list[str]
    field_confidence_map_list: list[dict[str, float]]


def calculate_average_non_empty_confidence(
    field_confidence_map_list: list[dict[str, float]],
    empty_fields: list[str] | None,
) -> float | None:
    """Mean confidence across non-empty fields. None when there are no such fields."""
    empty_set = set(empty_fields or [])
    scores = [
        conf
        for field_map in field_confidence_map_list
        for name, conf in field_map.items()
        if name not in empty_set
    ]
    if not scores:
        return None
    return sum(scores) / len(scores)


@dataclass
class BdaFieldProcessingResult:
    confidence: float
    is_empty: bool


def _extract_fields_recursive(
    data: dict[str, Any],
    parent_key: str,
    confidence_scores: list[float],
    empty_fields: list[str],
    field_confidence_map_list: list[dict[str, float]],
    field_values: dict[str, Any] | None = None,
    field_geometry: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Recursively process fields, handling both flat and nested structures.

    BDA returns nested objects (e.g. ``payment_details: {base_rent: {...}}``). We
    flatten them into dot-joined path names (``payment_details.base_rent``) because
    the flat form is the vocabulary every internal consumer wants: confidence
    averaging and empty-field counting iterate a flat ``[{name: conf}]`` list,
    ``FIELD_CONFIDENCE_SCORES`` is stored flat in DDB, and extraction-rule matching
    is plain set membership over these names. The API response re-nests these dotted
    names at the edge (``_nest_fields`` in response_builder); do not push the nested
    shape back through here.
    """
    for field_name, field_data in data.items():
        if not isinstance(field_data, dict):
            continue

        # Dot-join the parent path into the child name to flatten nested BDA fields.
        full_field_name = f"{parent_key}.{field_name}" if parent_key else field_name

        # check field is an actual extracted value (e.g. confidence score or value) or a nested structure
        if (
            BdaResponseFields.FIELD_CONFIDENCE in field_data
            or BdaResponseFields.FIELD_VALUE in field_data
        ):
            # extracted field - process it
            field_result = _process_single_field(full_field_name, field_data)
            field_confidence_map_list.append({full_field_name: field_result.confidence})

            if field_result.is_empty:
                empty_fields.append(full_field_name)
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
            # nested structure - recursion required
            _extract_fields_recursive(
                field_data,
                full_field_name,
                confidence_scores,
                empty_fields,
                field_confidence_map_list,
                field_values,
                field_geometry,
            )


def _process_single_field(field_name: str, field_data: dict[str, Any]) -> BdaFieldProcessingResult:
    """Process a single field and return its results."""
    confidence = field_data.get(BdaResponseFields.FIELD_CONFIDENCE, 0)
    value = field_data.get(BdaResponseFields.FIELD_VALUE, "")
    is_empty = len(str(value)) == 0

    logger.info(f"Extracted field name: {field_name}, confidence: {confidence}")

    return BdaFieldProcessingResult(confidence, is_empty)


def get_text_from_standard_blueprint(bda_result_json: dict[str, Any]) -> str | None:
    """Extract text from BDA standard output for both document and image modalities."""
    if not bda_result_json:
        return None

    semantic_modality = bda_result_json.get("metadata", {}).get("semantic_modality")

    if semantic_modality == "DOCUMENT" and bda_result_json.get("pages"):
        page = bda_result_json["pages"][0]
        text = page.get("representation", {}).get("text", "")
        if text:
            return str(text.strip())

    elif semantic_modality == "IMAGE" and bda_result_json.get("image"):
        image_data = bda_result_json["image"]
        text_words = image_data.get("text_words", [])
        words = [word.get("text", "") for word in text_words if word.get("text")]
        text = " ".join(words)
        if text:
            return str(text.strip())

    return None


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
                field_values,
                field_geometry if include_geometry else None,
            )

    metadata = BdaFieldProcessingData(
        confidence_scores=confidence_scores,
        empty_fields=empty_fields,
        field_confidence_map_list=field_confidence_map_list,
    )

    return (metadata, field_values, field_geometry)


def extract_field_metadata_from_bda_results(
    bda_result_json: dict[str, Any],
) -> BdaFieldProcessingData:
    """Extract only metadata (confidence, empty fields) from BDA result."""
    metadata, _, _ = extract_field_values_from_bda_results(bda_result_json)
    return metadata


def extract_region_from_bda_arn(bda_invocation_arn: str) -> str | None:
    """Extract AWS region from BDA invocation ARN."""
    try:
        # arn format: arn:aws:bedrock-data-automation:us-east-1:account:job/job-id
        parts = bda_invocation_arn.split(":")
        if len(parts) >= 4:
            return parts[3]  # Region is the 4th part
        return None
    except Exception as e:
        logger.error(f"Failed to extract region from ARN {bda_invocation_arn}: {e}")
        return None


def get_ddb_record_from_bda_output(
    output_bucket_name: str, output_object_key: str
) -> dict[str, Any] | None:
    """Resolve the full DDB record from a BDA output S3 location.

    Extracts the BDA invocation ID (last UUID in the path) and queries DDB
    to find the associated document record.

    Returns None if the invocation ID cannot be extracted or no record is found.
    """
    bda_output_s3_uri = f"s3://{output_bucket_name}/{output_object_key}"
    uuid_matches = re.findall(UUID_PATTERN, bda_output_s3_uri)
    if not uuid_matches:
        return None

    bda_invocation_id = str(uuid_mod.UUID(uuid_matches[-1]))

    table_name = get_required_env(EnvVars.DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME)
    index_name = get_required_env(EnvVars.DOCUMENTAI_DOCUMENT_METADATA_BDA_INVOCATION_ID_INDEX_NAME)

    items = ddb_service.query_by_key(
        table_name, index_name, DocumentMetadata.BDA_INVOCATION_ID, bda_invocation_id
    )

    if not items:
        return None

    return items[0]


def get_ddb_key_from_bda_output(output_bucket_name: str, output_object_key: str) -> str | None:
    """Resolve the DDB file_name key from a BDA output S3 location.

    Extracts the BDA invocation ID (last UUID in the path) and queries DDB
    to find the associated document record's file_name (partition key).

    Returns None if the invocation ID cannot be extracted or no record is found.
    """
    record = get_ddb_record_from_bda_output(output_bucket_name, output_object_key)
    if not record:
        return None
    return record.get(DocumentMetadata.FILE_NAME)
