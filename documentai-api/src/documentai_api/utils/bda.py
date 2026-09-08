import re
import uuid as uuid_mod
from dataclasses import dataclass
from typing import Any

from documentai_api.config.constants import (
    UUID_PATTERN,
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


def get_bda_result_json(bda_result_uri: str) -> dict[str, Any] | None:
    """Read and return BDA result JSON from S3."""
    from documentai_api.config.env import get_aws_config
    from documentai_api.services import s3 as s3_service
    from documentai_api.utils.json_parsing import parse_json_object
    from documentai_api.utils.s3 import parse_s3_uri

    if not bda_result_uri:
        return None

    try:
        s3_parts = bda_result_uri.replace("s3://", "").split("/", 1)
        result_bucket = s3_parts[0]
        result_key = s3_parts[1]

        # Validate the bucket is the configured output bucket to prevent SSRF
        # via a crafted BDA response pointing at an arbitrary S3 location.
        output_location = get_aws_config().documentai_output_location
        if output_location:
            expected_bucket, _ = parse_s3_uri(output_location)
            if result_bucket != expected_bucket:
                logger.error(
                    f"BDA result URI bucket {result_bucket!r} does not match "
                    f"expected output bucket {expected_bucket!r}"
                )
                return None

        bda_result_object = s3_service.get_object(result_bucket, result_key)
        return parse_json_object(bda_result_object["Body"].read(), context="BDA result JSON")
    except Exception as e:
        logger.error(f"Failed to read result JSON: {e}")
        return None


def extract_bda_output_s3_uri(
    bda_output_bucket_name: str, bda_output_object_key: str
) -> str | None:
    """Read and parse BDA job metadata from S3."""
    from documentai_api.services import s3 as s3_service
    from documentai_api.utils.json_parsing import parse_json_object

    metadata_response = s3_service.get_object(bda_output_bucket_name, bda_output_object_key)
    job_metadata = parse_json_object(metadata_response["Body"].read(), context="BDA job metadata")
    if job_metadata is None:
        return None

    try:
        for output_meta in job_metadata.get("output_metadata", []):
            for segment in output_meta.get("segment_metadata", []):
                if "custom_output_path" in segment:
                    return str(segment["custom_output_path"])

                if "standard_output_path" in segment:
                    return str(segment["standard_output_path"])

        return None
    except (TypeError, AttributeError) as e:
        logger.error(f"Failed to extract BDA result uri: {e}")
        return None
