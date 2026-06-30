"""Utilities for Textract AnalyzeID: parsing, orchestration, and DDB finalization."""

import json
from datetime import UTC, datetime
from typing import Any

from documentai_api.config.constants import ExtractMethod, TextractConfig
from documentai_api.config.env import EnvVars, get_required_env
from documentai_api.logging import get_logger
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.dates import strip_time
from documentai_api.utils.response_codes import ResponseCodes

logger = get_logger(__name__)


def extract_fields_from_analyze_id(
    response: dict[str, Any], field_map: dict[str, str]
) -> dict[str, Any]:
    """Extract structured fields from Textract AnalyzeID response using a field map.

    Args:
        response: Raw Textract AnalyzeID response
        field_map: Maps Textract field type (e.g. "FIRST_NAME") to BDA field name

    Returns dict of {bda_field_name: {"confidence": float, "value": str}}

    TODO: AnalyzeID returns a Blocks array (LINE/WORD) with full BoundingBox geometry.
    These aren't linked to IdentityDocumentFields directly, but field values could be
    matched to blocks by text content to provide bounding boxes in the UI. Requires
    fuzzy text matching since some fields span multiple words/lines.
    """
    fields = {}

    for doc in response.get("IdentityDocuments", []):
        for field in doc.get("IdentityDocumentFields", []):
            field_type = field.get("Type", {}).get("Text", "")

            bda_name = field_map.get(field_type)
            if not bda_name:
                continue

            value_detection = field.get("ValueDetection", {})
            value = value_detection.get("Text", "")
            confidence = value_detection.get("Confidence", 0.0)

            # use normalized value for dates if available
            normalized = value_detection.get("NormalizedValue", {})
            if normalized.get("Value"):
                value = strip_time(normalized["Value"])

            fields[bda_name] = {
                "confidence": round(confidence / 100.0, 2),
                "value": value,
            }

    return fields


def get_id_type(response: dict[str, Any]) -> str | None:
    """Extract ID type from AnalyzeID response."""
    for doc in response.get("IdentityDocuments", []):
        for field in doc.get("IdentityDocumentFields", []):
            if field.get("Type", {}).get("Text") == "ID_TYPE":
                value: str | None = field.get("ValueDetection", {}).get("Text")
                return value
    return None


def extract_field_values_from_textract_results(
    result_json: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    """Extract field confidence metadata and values from stored Textract results.

    Returns (metadata_dict, field_values_dict) where metadata_dict has:
      - field_confidence_map_list: list of {name: confidence}
      - empty_fields: list of field names with no value
    """
    fields = result_json.get("fields", {})

    confidence_scores: list[float] = []
    empty_fields: list[str] = []
    field_confidence_map_list: list[dict[str, float]] = []
    field_values: dict[str, str] = {}

    for name, data in fields.items():
        conf = data["confidence"]
        value = data.get("value", "")

        field_confidence_map_list.append({name: conf})

        if not value:
            empty_fields.append(name)
        else:
            confidence_scores.append(conf)

        field_values[name] = value

    metadata = {
        "field_confidence_map_list": field_confidence_map_list,
        "empty_fields": empty_fields,
    }
    return metadata, field_values


# =============================================================================
# Orchestration: try Textract and finalize DDB record
# =============================================================================


def try_textract_identity(
    preclassification_category: str,
    content_type: str,
    file_bytes: bytes,
    ddb_key: str,
) -> dict[str, Any] | None:
    """Attempt Textract AnalyzeID if the document is an eligible identity type.

    Returns a result dict on success, or None if Textract should not be used
    (flag off, wrong category, unsupported content type, or Textract failure).
    On failure, logs a warning and returns None so the caller falls through to BDA.
    """
    from documentai_api.utils.ssm import is_textract_identity_enabled

    if not is_textract_identity_enabled():
        return None

    if preclassification_category not in TextractConfig.IDENTITY_PRECLASSIFICATION_CATEGORIES:
        return None

    if content_type not in TextractConfig.SUPPORTED_CONTENT_TYPES:
        return None

    try:
        from documentai_api.mappings import get_bda_field_map, get_document_class
        from documentai_api.services import s3 as s3_service
        from documentai_api.services.textract import analyze_id
        from documentai_api.utils import s3 as s3_utils
        from documentai_api.utils.ddb import get_elapsed_time_seconds, set_extract_method

        extract_started_at = datetime.now(UTC)
        textract_response = analyze_id(file_bytes)
        extract_completed_at = datetime.now(UTC)

        id_type = get_id_type(textract_response)
        matched_document_class = get_document_class(id_type)
        field_map = get_bda_field_map(matched_document_class) if matched_document_class else {}

        fields = extract_fields_from_analyze_id(textract_response, field_map)

        # Unrecognized ID type or no mapped fields — fall through to BDA
        if not matched_document_class or not fields:
            logger.info(
                f"Textract could not map document for {ddb_key} "
                f"(id_type={id_type}, class={matched_document_class}, fields={len(fields)}), "
                f"falling back to BDA"
            )
            return None

        # Textract succeeded — commit extract method + start time
        set_extract_method(ddb_key, ExtractMethod.TEXTRACT, extract_started_at.isoformat())

        # Write mapped result to S3 (reuses the BDA output location so
        # response_builder can read it back via bda_output_s3_uri)
        output_location = get_required_env(EnvVars.DOCUMENTAI_OUTPUT_LOCATION)
        output_bucket, output_prefix = s3_utils.parse_s3_uri(output_location)
        textract_s3_key = f"{output_prefix}/textract/{ddb_key}.json"
        textract_s3_uri = f"s3://{output_bucket}/{textract_s3_key}"

        s3_service.put_object(
            output_bucket,
            textract_s3_key,
            json.dumps({"source": "textract", "fields": fields}).encode(),
            content_type="application/json",
        )

        field_confidence_scores = [{name: data["confidence"]} for name, data in fields.items()]
        field_empty_list = [name for name, data in fields.items() if not data.get("value")]
        extract_time = get_elapsed_time_seconds(extract_started_at, extract_completed_at)

        logger.info(
            f"Textract identified document as {matched_document_class} "
            f"with {len(field_confidence_scores)} fields in {extract_time}s"
        )

        return {
            "matched_document_class": matched_document_class,
            "field_confidence_scores": field_confidence_scores,
            "field_empty_list": field_empty_list,
            "textract_s3_uri": textract_s3_uri,
            "extract_started_at": extract_started_at,
            "extract_completed_at": extract_completed_at,
            "extract_time": extract_time,
        }

    except Exception as e:
        logger.warning(f"Textract AnalyzeID failed for {ddb_key}, falling back to BDA: {e}")
        return None


def finalize_textract_result(
    ddb_key: str,
    textract_result: dict[str, Any],
    user_provided_document_category: str | None,
) -> None:
    """Update the DDB record with Textract extraction results.

    extract method and start time are already written by try_textract_identity.
    This delegates to classify_as_success which triggers _build_completion_timing
    to calculate elapsed time from bdaStartedAt.
    """
    from documentai_api.utils.bda import calculate_average_non_empty_confidence
    from documentai_api.utils.ddb import get_ddb_record
    from documentai_api.utils.document_lifecycle import classify_as_success
    from documentai_api.utils.dto import ClassificationData
    from documentai_api.utils.tenants import get_extraction_confidence_floor

    field_empty_list = textract_result.get("field_empty_list", [])

    data = ClassificationData(
        matched_document_class=textract_result["matched_document_class"],
        field_confidence_scores=textract_result["field_confidence_scores"],
        field_empty_list=field_empty_list,
        bda_output_s3_uri=textract_result["textract_s3_uri"],
    )

    # Evaluate confidence floor (same as BDA path in bda_output_processor)
    tenant_id = (get_ddb_record(ddb_key) or {}).get(DocumentMetadata.TENANT_ID)
    avg = calculate_average_non_empty_confidence(
        data.field_confidence_scores or [], data.field_empty_list
    )
    below_floor = avg is not None and avg < get_extraction_confidence_floor(tenant_id)

    classify_as_success(
        object_key=ddb_key,
        response_code=ResponseCodes.SUCCESS,
        data=data,
        below_extraction_confidence_floor=below_floor,
    )
