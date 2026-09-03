"""Utilities for Textract AnalyzeID: parsing and field extraction helpers."""

import json
from typing import Any

from opentelemetry import trace

from documentai_api.logging import get_logger
from documentai_api.utils.dates import strip_time

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)

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
            value_type = normalized.get("ValueType", "string").lower()
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
                "fieldType": value_type,
            }
            if geometry:
                field_data["geometry"] = geometry

            fields[bda_name] = field_data

        # If any date fields have duplicate values, AnalyzeID assigned the same
        # block to multiple fields. We can't reliably resolve which is which
        # without document-layout assumptions, so fall through to BDA.
        date_values = [
            f["value"] for f in fields.values() if f.get("fieldType") == "date" and f.get("value")
        ]
        if len(date_values) != len(set(date_values)):
            logger.info("Duplicate date values detected, falling back to BDA")
            return {}

    return fields


def _build_geometry_entry(geometry: dict[str, Any], page: int = 1) -> dict[str, Any]:
    """Build a geometry entry from a Textract Geometry dict.

    Normalizes Textract's PascalCase keys (Top, Left, Width, Height) to lowercase
    to match BDA's geometry format.
    """
    entry: dict[str, Any] = {
        "boundingBox": {k.lower(): v for k, v in geometry["BoundingBox"].items()},
    }
    polygon = geometry.get("Polygon")
    if polygon:
        entry["vertices"] = [{"x": p["X"], "y": p["Y"]} for p in polygon]
    entry["page"] = page
    return entry


def _build_block_geometry_index(blocks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Build a text-to-geometry lookup from Textract Blocks.

    Indexes LINE blocks first (for multi-word matches), then WORD blocks.
    Returns {text: [{"boundingBox": {...}, "vertices": [...]}]} matching the BDA geometry format.
    """
    index: dict[str, list[dict[str, Any]]] = {}

    # LINE blocks first -- these cover multi-word field values (e.g. "100 MARKET STREET")
    for block in blocks:
        if block.get("BlockType") != "LINE":
            continue
        text = block.get("Text", "")
        geom = block.get("Geometry", {})
        if text and geom.get("BoundingBox") and text not in index:
            index[text] = [_build_geometry_entry(geom, page=block.get("Page", 0) + 1)]

    # WORD blocks -- fill in single-word values not already covered by LINE
    for block in blocks:
        if block.get("BlockType") != "WORD":
            continue
        text = block.get("Text", "")
        geom = block.get("Geometry", {})
        if text and geom.get("BoundingBox") and text not in index:
            index[text] = [_build_geometry_entry(geom, page=block.get("Page", 0) + 1)]

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
        geom = best_match.get("Geometry", {})
        if geom.get("BoundingBox"):
            return [_build_geometry_entry(geom)]

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
    supplemental_fields: dict[str, str],
    supplemental_prompt: str,
) -> dict[str, Any]:
    """Extract supplemental fields from Blocks via Nova Micro.

    Sends WORD blocks (text + bounding box) to Nova Micro and asks it to identify
    fields not normalized by AnalyzeID.

    Returns dict of {bda_field_name: {"confidence": float, "value": str, "geometry": list | None}}
    """
    word_blocks = _get_word_blocks(blocks)
    if not word_blocks:
        return {}

    try:
        extracted_fields = _call_nova_supplemental(
            word_blocks, supplemental_fields, supplemental_prompt
        )
    except Exception as e:
        logger.warning(f"Nova supplemental field extraction failed: {e}")
        return {}

    if not extracted_fields:
        return {}

    fields = _match_nova_results_to_blocks(extracted_fields, word_blocks, supplemental_fields)
    logger.info(f"Nova supplemental: extracted {len(fields)} fields")
    return fields


def _get_word_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract WORD blocks with text, bounding box, vertices, and confidence.

    Normalizes Textract's PascalCase BoundingBox/Polygon keys to lowercase
    to match BDA's geometry format.
    """
    result = []
    for b in blocks:
        if b.get("BlockType") != "WORD" or not b.get("Text"):
            continue
        geom = b.get("Geometry", {})
        raw_bbox = geom.get("BoundingBox")
        if not raw_bbox:
            continue
        entry: dict[str, Any] = {
            "text": b["Text"],
            "boundingBox": {k.lower(): v for k, v in raw_bbox.items()},
            "confidence": b.get("Confidence", 0.0),
        }
        polygon = geom.get("Polygon")
        if polygon:
            entry["vertices"] = [{"x": p["X"], "y": p["Y"]} for p in polygon]
        result.append(entry)
    return result


def _call_nova_supplemental(
    word_blocks: list[dict[str, Any]],
    supplemental_fields: dict[str, str],
    supplemental_prompt: str,
) -> list[dict[str, Any]]:
    """Call Nova Micro to identify supplemental fields from word blocks."""
    from documentai_api.services.bedrock import invoke_model
    from documentai_api.utils.json_parsing import parse_llm_json

    field_descriptions = "\n".join(
        f"- {name}: {desc}" for name, desc in supplemental_fields.items()
    )

    # Embed an explicit block index so Nova can reference blocks by position.
    # Text-based matching proved brittle - synthetic-drivers-license-desk-background.jpg
    # eye color block contained full text "18 EYES:BRO" (field 18, value "BRO" = brown),
    # Nova Micro consistently extracted "BRO" even after numerous prompt iterations.
    # Indexing by position ties extracted values to specific blocks regardless of
    # how the model reads the surrounding text.
    indexed_blocks = [{"index": i, **b} for i, b in enumerate(word_blocks)]

    prompt = supplemental_prompt.format(
        field_descriptions=field_descriptions,
        blocks_json=json.dumps(indexed_blocks),
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
    supplemental_fields: dict[str, str],
) -> dict[str, Any]:
    """Match Nova's identified fields back to block geometry and confidence."""
    fields: dict[str, Any] = {}
    for item in extracted_fields:
        field_name = item.get("field_name", "")
        value = item.get("value", "")
        block_index = item.get("block_index")

        if field_name not in supplemental_fields or not value:
            continue

        if block_index is None or not isinstance(block_index, int):
            continue

        if block_index < 0 or block_index >= len(word_blocks):
            continue

        matched_block = word_blocks[block_index]

        # Validate block text matches value (case-insensitive). If not, find
        # the correct block - Nova sometimes points to the wrong duplicate.
        if not _block_text_matches(matched_block["text"], value):
            fallback = _find_matching_block(word_blocks, value)
            if fallback is not None:
                matched_block = fallback
            # If no fallback found, use Nova's original (best effort)

        geom_entry: dict[str, Any] = {"boundingBox": matched_block["boundingBox"]}
        if "vertices" in matched_block:
            geom_entry["vertices"] = matched_block["vertices"]
        geom_entry["page"] = 1

        field_data: dict[str, Any] = {
            "confidence": round(matched_block["confidence"] / 100.0, 2),
            "value": value,
            "fieldType": "string",
            "geometry": [geom_entry],
        }

        fields[field_name] = field_data

    return fields


def _block_text_matches(block_text: str, value: str) -> bool:
    """Check if block text matches the value (case-insensitive).

    Short values (<=2 chars) require exact match to avoid false positives
    (e.g. "F" matching "FIRST"). Longer values allow substring containment
    for multi-word matching (e.g. "UNITED STATES" matching block "States").
    """
    bt = block_text.lower()
    v = value.lower()
    if len(v) <= 2:
        return bt == v
    return bt == v or bt in v or v in bt


def _find_matching_block(word_blocks: list[dict[str, Any]], value: str) -> dict[str, Any] | None:
    """Find the rightmost block whose text matches the value.

    When duplicate text appears (e.g. "UNITED STATES" in header vs data area),
    the rightmost instance is typically the data field value.
    Short values (<=2 chars) require exact match.
    """
    best: dict[str, Any] | None = None
    best_left = -1.0

    for block in word_blocks:
        if _block_text_matches(block["text"], value):
            left = block["boundingBox"].get("left", 0)
            if left > best_left:
                best = block
                best_left = left

    return best
