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
    fields_missing_geometry: list[str] | None = None


@dataclass
class BdaFieldProcessingResult:
    confidence: float
    is_empty: bool
    has_geometry: bool = True


@dataclass
class MatchedBlueprintInfo:
    name: str
    confidence: float | None


def calculate_average_non_empty_confidence(
    field_confidence_map_list: list[dict[str, float]],
    empty_fields: list[str] | None,
    fields_missing_geometry: list[str] | None = None,
) -> float | None:
    """Mean confidence across non-empty, non-hallucinated fields. None when there are no such fields."""
    excluded = set(empty_fields or []) | set(fields_missing_geometry or [])
    scores = [
        conf
        for field_map in field_confidence_map_list
        for name, conf in field_map.items()
        if name not in excluded
    ]
    if not scores:
        return None
    return sum(scores) / len(scores)


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


def get_matched_blueprint(bda_result_json: dict[str, Any]) -> MatchedBlueprintInfo:
    """Extract matched blueprint name and confidence from BDA result JSON."""
    matched_blueprint = bda_result_json.get(BdaResponseFields.MATCHED_BLUEPRINT, {})
    return MatchedBlueprintInfo(
        name=matched_blueprint.get(BdaResponseFields.MATCHED_BLUEPRINT_NAME),
        confidence=matched_blueprint.get(BdaResponseFields.MATCHED_BLUEPRINT_CONFIDENCE),
    )
