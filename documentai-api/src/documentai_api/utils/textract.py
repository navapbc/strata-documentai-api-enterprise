"""Utilities for Textract AnalyzeID: parsing, orchestration, and DDB finalization."""

import json
from datetime import UTC, datetime
from typing import Any

from documentai_api.config.constants import ExtractMethod, TextractConfig
from documentai_api.config.env import EnvVars, get_required_env
from documentai_api.logging import get_logger
from documentai_api.mappings.textract.us_drivers_licenses import (
    NON_NORMALIZED_ANALYZE_ID_FIELDS,
    NOVA_SUPPLEMENTAL_PROMPT,
)
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.dates import strip_time
from documentai_api.utils.response_codes import ResponseCodes

logger = get_logger(__name__)

NOVA_MICRO_MODEL_ID = "us.amazon.nova-micro-v1:0"


def _get_supplemental_model_id() -> str:
    """Resolve supplemental extraction model ID from SSM, with hardcoded fallback."""
    from documentai_api.config.env import get_aws_config
    from documentai_api.utils.ssm import get_parameter_value

    param_name = get_aws_config().bedrock_supplemental_extraction_model_id_param
    if not param_name:
        return NOVA_MICRO_MODEL_ID
    return get_parameter_value(param_name, default=NOVA_MICRO_MODEL_ID)


def extract_fields_from_analyze_id(
    response: dict[str, Any], field_map: dict[str, str]
) -> dict[str, Any]:
    """Extract structured fields from Textract AnalyzeID response using a field map.

    Args:
        response: Raw Textract AnalyzeID response
        field_map: Maps Textract field type (e.g. "FIRST_NAME") to BDA field name

    Returns dict of {bda_field_name: {"confidence": float, "value": str, "geometry": list | None}}
    """
    fields = {}

    for doc in response.get("IdentityDocuments", []):
        # build text-to-geometry lookup from Blocks
        all_blocks = doc.get("Blocks", [])
        block_geometry = _build_block_geometry_index(all_blocks)
        word_blocks = [b for b in all_blocks if b.get("BlockType") == "WORD"]

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

            # match geometry from blocks by raw text (pre-normalization)
            raw_text = value_detection.get("Text", "")
            geometry = (
                _find_geometry_with_fallback(raw_text, block_geometry, word_blocks)
                if raw_text
                else None
            )

            field_data: dict[str, Any] = {
                "confidence": round(confidence / 100.0, 2),
                "value": value,
            }
            if geometry:
                field_data["geometry"] = geometry

            fields[bda_name] = field_data

    return fields


def _build_block_geometry_index(blocks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Build a text-to-geometry lookup from Textract Blocks.

    Indexes LINE blocks first (for multi-word matches), then WORD blocks.
    Returns {text: [{"boundingBox": {...}}]} matching the BDA geometry format.
    """
    index: dict[str, list[dict[str, Any]]] = {}

    # LINE blocks first -- these cover multi-word field values (e.g. "100 MARKET STREET")
    for block in blocks:
        if block.get("BlockType") != "LINE":
            continue
        text = block.get("Text", "")
        bbox = block.get("Geometry", {}).get("BoundingBox")
        if text and bbox and text not in index:
            index[text] = [{"boundingBox": bbox}]

    # WORD blocks -- fill in single-word values not already covered by LINE
    for block in blocks:
        if block.get("BlockType") != "WORD":
            continue
        text = block.get("Text", "")
        bbox = block.get("Geometry", {}).get("BoundingBox")
        if text and bbox and text not in index:
            index[text] = [{"boundingBox": bbox}]

    return index


def _clean_text(text: str) -> str:
    """Normalize text for geometry matching: lowercase, strip punctuation and whitespace."""
    import string

    return text.lower().strip().translate(str.maketrans("", "", string.punctuation))


def _find_geometry_with_fallback(
    field_value: str,
    block_index: dict[str, list[dict[str, Any]]],
    word_blocks: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    """Find geometry for a field value with exact match then cleaned-text fallback.

    1. Exact match against the block index (LINE then WORD priority).
    2. Cleaned fallback: strip punctuation from both sides and compare against
       WORD blocks. Picks the shortest matching block text for tightest bbox.
    """
    # exact match
    if field_value in block_index:
        return block_index[field_value]

    if not field_value:
        return None

    # cleaned-text fallback on WORD blocks
    cleaned_value = _clean_text(field_value)
    if not cleaned_value:
        return None

    best_match: dict[str, Any] | None = None
    best_length = float("inf")

    for block in word_blocks:
        block_text = block.get("Text", "")
        if _clean_text(block_text) == cleaned_value and len(block_text) < best_length:
            best_match = block
            best_length = len(block_text)

    if best_match:
        bbox = best_match.get("Geometry", {}).get("BoundingBox")
        if bbox:
            return [{"boundingBox": bbox}]

    return None


def get_id_type(response: dict[str, Any]) -> str | None:
    """Extract ID type from AnalyzeID response."""
    for doc in response.get("IdentityDocuments", []):
        for field in doc.get("IdentityDocumentFields", []):
            if field.get("Type", {}).get("Text") == "ID_TYPE":
                value: str | None = field.get("ValueDetection", {}).get("Text")
                return value
    return None


def extract_supplemental_fields_via_nova(
    blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Extract physical descriptor fields from Blocks via Nova Micro.

    Sends WORD blocks (text + bounding box) to Nova Micro and asks it to identify
    fields not normalized by AnalyzeID (sex, height, eye color, etc.).

    Returns dict of {bda_field_name: {"confidence": float, "value": str, "geometry": list | None}}
    """
    word_blocks = _get_word_blocks(blocks)
    if not word_blocks:
        return {}

    try:
        extracted_fields = _call_nova_supplemental(word_blocks)
    except Exception as e:
        logger.warning(f"Nova supplemental field extraction failed: {e}")
        return {}

    if not extracted_fields:
        return {}

    fields = _match_nova_results_to_blocks(extracted_fields, word_blocks)
    logger.info(f"Nova supplemental: extracted {len(fields)} physical descriptor fields")
    return fields


def _get_word_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract WORD blocks with text, bounding box, and confidence."""
    return [
        {
            "text": b["Text"],
            "boundingBox": b["Geometry"]["BoundingBox"],
            "confidence": b.get("Confidence", 0.0),
        }
        for b in blocks
        if b.get("BlockType") == "WORD"
        and b.get("Text")
        and b.get("Geometry", {}).get("BoundingBox")
    ]


def _call_nova_supplemental(word_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Call Nova Micro to identify physical descriptor fields from word blocks."""
    from documentai_api.services.bedrock import invoke_model
    from documentai_api.utils.json_parsing import parse_llm_json

    field_descriptions = "\n".join(
        f"- {name}: {desc}" for name, desc in NON_NORMALIZED_ANALYZE_ID_FIELDS.items()
    )

    prompt = NOVA_SUPPLEMENTAL_PROMPT.format(
        field_descriptions=field_descriptions,
        blocks_json=json.dumps(word_blocks),
    )

    response = invoke_model(
        model_id=_get_supplemental_model_id(),
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        max_tokens=512,
        temperature=0.0,
    )

    output_text = response["output"]["message"]["content"][0]["text"]
    result = parse_llm_json(output_text, context="Nova supplemental fields")
    if not result:
        return []

    return list(result.get("fields", []))


def _match_nova_results_to_blocks(
    extracted_fields: list[dict[str, Any]],
    word_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Match Nova's identified fields back to block geometry and confidence."""
    block_lookup = {b["text"]: b for b in word_blocks}

    fields: dict[str, Any] = {}
    for item in extracted_fields:
        field_name = item.get("field_name", "")
        value = item.get("value", "")
        block_text = item.get("block_text", "")

        if field_name not in NON_NORMALIZED_ANALYZE_ID_FIELDS or not value:
            continue

        # match block: exact first, then cleaned-text fallback
        matched_block = block_lookup.get(block_text)
        if not matched_block and block_text:
            cleaned = _clean_text(block_text)
            for b in word_blocks:
                if _clean_text(b["text"]) == cleaned:
                    matched_block = b
                    break

        # no matched block = no OCR verification, skip the field
        if not matched_block:
            continue

        field_data: dict[str, Any] = {
            "confidence": round(matched_block["confidence"] / 100.0, 2),
            "value": value,
            "geometry": [{"boundingBox": matched_block["boundingBox"]}],
        }

        fields[field_name] = field_data

    return fields


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
            field_geometry[name] = {"geometry": data["geometry"]}

    metadata = {
        "field_confidence_map_list": field_confidence_map_list,
        "empty_fields": empty_fields,
    }
    return metadata, field_values, field_geometry


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
        from documentai_api.utils.ddb import set_extract_method
        from documentai_api.utils.extraction_timing import get_elapsed_time_seconds

        extract_started_at = datetime.now(UTC)
        textract_response = analyze_id(file_bytes)
        extract_completed_at = datetime.now(UTC)

        id_type = get_id_type(textract_response)
        matched_document_class = get_document_class(id_type)
        field_map = get_bda_field_map(matched_document_class) if matched_document_class else {}

        fields = extract_fields_from_analyze_id(textract_response, field_map)

        # Supplemental pass: extract physical descriptors via Nova Micro
        all_blocks = []
        for doc in textract_response.get("IdentityDocuments", []):
            all_blocks.extend(doc.get("Blocks", []))
        if all_blocks:
            supplemental = extract_supplemental_fields_via_nova(all_blocks)
            fields.update(supplemental)

        # Unrecognized ID type or no mapped fields -- fall through to BDA
        if not matched_document_class or not fields:
            logger.info(
                f"Textract could not map document for {ddb_key} "
                f"(id_type={id_type}, class={matched_document_class}, fields={len(fields)}), "
                f"falling back to BDA"
            )
            return None

        # Textract succeeded - commit extract method + start time
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
