"""LLM extraction: instructor + Bedrock against Textract OCR blocks."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from opentelemetry import trace

from documentai_api.dtos.extraction import ExtractionResult
from documentai_api.logging import get_logger
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.ddb import get_ddb_record

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)


def compute_confidence(
    citation: str | None,
    ocr_blocks: list[dict[str, Any]],
) -> float:
    """Derive confidence from Textract word-level scores at the citation span."""
    if not citation or not citation.strip():
        return 0.0

    import difflib

    line_blocks = [b for b in ocr_blocks if b.get("BlockType") == "LINE" and b.get("Text")]
    word_blocks = [b for b in ocr_blocks if b.get("BlockType") == "WORD"]

    best_ratio = 0.0
    best_line: dict[str, Any] | None = None

    for block in line_blocks:
        ratio = difflib.SequenceMatcher(None, citation.lower(), block["Text"].lower()).ratio()

        if ratio > best_ratio:
            best_ratio = ratio
            best_line = block

    if best_ratio < 0.6 or best_line is None:
        return 0.0

    line_bb = best_line.get("Geometry", {}).get("BoundingBox", {})

    if not line_bb:
        return round(best_ratio, 2)

    left, top = line_bb.get("Left", 0), line_bb.get("Top", 0)
    right = left + line_bb.get("Width", 0)
    bottom = top + line_bb.get("Height", 0)

    word_confidences: list[float] = []

    for w in word_blocks:
        w_bb = w.get("Geometry", {}).get("BoundingBox", {})

        if not w_bb:
            continue

        cx = w_bb.get("Left", 0) + w_bb.get("Width", 0) / 2
        cy = w_bb.get("Top", 0) + w_bb.get("Height", 0) / 2

        if left <= cx <= right and top <= cy <= bottom:
            word_confidences.append(w.get("Confidence", 0.0))

    if not word_confidences:
        return round(best_ratio, 2)

    return round(sum(word_confidences) / len(word_confidences) / 100.0, 4)


def ocr_blocks_to_text(blocks: list[dict[str, Any]]) -> str:
    """Reconstruct page text from Textract LINE blocks in reading order."""
    return "\n".join(b["Text"] for b in blocks if b.get("BlockType") == "LINE" and b.get("Text"))


def _extract(
    ddb_key: str,
    document_type: str,
    ocr_blocks: list[dict[str, Any]],
    processing_started_at: datetime,
) -> tuple[ExtractionResult, Decimal, int | None, int | None]:
    """Run instructor extraction and return (ExtractionResult, duration, input_tokens, output_tokens)."""
    import instructor

    from documentai_api.config.constants import ExtractMethod
    from documentai_api.services.aws_client_factory import AWSClientFactory
    from documentai_api.utils.llm_blueprint_models import build_blueprint_model
    from documentai_api.utils.schemas import get_document_schema
    from documentai_api.utils.ssm import get_llm_extractor_model_id
    from documentai_api.utils.textract import build_citation_index, match_citation_to_geometry

    schema = get_document_schema(document_type)

    if not schema:
        raise ValueError(f"No schema found for document type '{document_type}'")

    ocr_text = ocr_blocks_to_text(ocr_blocks)

    if not ocr_text.strip():
        raise ValueError(f"No OCR text available for {ddb_key}")

    model_id = get_llm_extractor_model_id()
    blueprint_model, field_name_map = build_blueprint_model(schema)

    bedrock_client = AWSClientFactory.get_bedrock_runtime_client()
    client = instructor.from_bedrock(bedrock_client, mode=instructor.Mode.BEDROCK_JSON)

    started_at = processing_started_at
    input_tokens: int | None = None
    output_tokens: int | None = None

    with tracer.start_as_current_span("llm.extraction") as span:
        span.set_attribute("document.key", ddb_key)
        span.set_attribute("document.type", document_type)
        span.set_attribute("llm.model_id", model_id)
        response, completion = client.chat.completions.create_with_completion(
            model=model_id,
            response_model=blueprint_model,
            messages=[{"role": "user", "content": ocr_text}],
            temperature=0.0,
        )
        usage = completion.usage if hasattr(completion, "usage") and completion.usage else None
        input_tokens = usage.input_tokens if usage and hasattr(usage, "input_tokens") else None
        output_tokens = usage.output_tokens if usage and hasattr(usage, "output_tokens") else None

        if input_tokens is not None:
            span.set_attribute("llm.input_tokens", input_tokens)

        if output_tokens is not None:
            span.set_attribute("llm.output_tokens", output_tokens)

    block_index, word_blocks = build_citation_index(ocr_blocks)
    field_type_map = {f.name: f.type for f in schema.fields}
    field_confidence_scores: list[dict[str, float]] = []
    field_empty_list: list[str] = []
    fields_output: dict[str, Any] = {}

    for field_name_underscored in blueprint_model.model_fields:
        extracted = getattr(response, field_name_underscored, None)

        if extracted is None:
            continue

        field_name = field_name_map.get(field_name_underscored, field_name_underscored)
        value = extracted.value if extracted.value is not None else ""
        conf = compute_confidence(extracted.text_citation, ocr_blocks)
        field_confidence_scores.append({field_name: conf})

        if not value:
            field_empty_list.append(field_name)

        field_entry: dict[str, Any] = {
            "value": value,
            "confidence": conf,
            "text_citation": extracted.text_citation,
            "fieldType": field_type_map.get(field_name, "string"),
        }

        if extracted.text_citation:
            geometry = match_citation_to_geometry(extracted.text_citation, block_index, word_blocks)

            if geometry:
                field_entry["geometry"] = geometry

        fields_output[field_name] = field_entry

    completed_at = datetime.now(UTC)
    duration = Decimal(str(round((completed_at - started_at).total_seconds(), 3)))
    body = json.dumps(
        {
            "source": ExtractMethod.LLM,
            "document_type": document_type,
            "model_id": model_id,
            "fields": fields_output,
        }
    ).encode()

    result = ExtractionResult(
        document_type=document_type,
        body=body,
        processing_started_at=started_at,
        processing_completed_at=completed_at,
        field_confidence_scores=field_confidence_scores,
        field_empty_list=field_empty_list,
    )
    return result, duration, input_tokens, output_tokens


def _write_llm_telemetry(
    ddb_key: str,
    document_type: str,
    duration: Decimal,
    input_tokens: int | None,
    output_tokens: int | None,
) -> None:
    from documentai_api.config.env import get_env_config
    from documentai_api.services import ddb as ddb_service
    from documentai_api.utils.ssm import get_llm_extractor_model_id

    model_id = get_llm_extractor_model_id()
    table_name = get_env_config().get_document_metadata_table_name
    updates: dict[str, Any] = {
        DocumentMetadata.LLM_DOCUMENT_TYPE: document_type,
        DocumentMetadata.LLM_MODEL_ID: model_id,
        DocumentMetadata.LLM_DURATION_SECONDS: duration,
    }

    if input_tokens is not None:
        updates[DocumentMetadata.LLM_INPUT_TOKENS] = input_tokens

    if output_tokens is not None:
        updates[DocumentMetadata.LLM_OUTPUT_TOKENS] = output_tokens

    set_expr = "SET " + ", ".join(f"{k} = :{k}" for k in updates)
    expr_values = {f":{k}": v for k, v in updates.items()}
    ddb_service.update_item(table_name, {"fileName": ddb_key}, set_expr, expr_values)


def run_llm_extraction(
    ddb_key: str,
    document_type: str,
    ocr_blocks: list[dict[str, Any]],
) -> ExtractionResult:
    """Primary LLM extraction path. Raises on failure."""
    ddb_record = get_ddb_record(ddb_key) or {}
    started_at_str = ddb_record.get(DocumentMetadata.EXTRACTION_STARTED_AT)
    processing_started_at = (
        datetime.fromisoformat(started_at_str) if started_at_str else datetime.now(UTC)
    )

    with tracer.start_as_current_span("llm.run_extraction") as span:
        span.set_attribute("document.key", ddb_key)
        span.set_attribute("document.type", document_type)

        result, duration, input_tokens, output_tokens = _extract(
            ddb_key, document_type, ocr_blocks, processing_started_at
        )
        result.processing_duration_seconds = duration
        _write_llm_telemetry(ddb_key, document_type, duration, input_tokens, output_tokens)

        span.set_attribute("llm.field_count", len(result.field_confidence_scores))

    logger.info(
        f"LLM extraction complete for {ddb_key}",
        extra={
            "document_type": document_type,
            "field_count": len(result.field_confidence_scores),
            "duration_seconds": str(duration),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    )

    return result
