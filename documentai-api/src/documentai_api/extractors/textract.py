"""Textract extractor: AnalyzeID extraction into an ExtractionResult."""

import json
from datetime import UTC, datetime

from opentelemetry import trace

from documentai_api.config.constants import ExtractMethod, TextractConfig
from documentai_api.config.env import EnvVars, get_required_env
from documentai_api.dtos.extraction import ExtractionResult
from documentai_api.logging import get_logger
from documentai_api.mappings import get_bda_field_map, get_document_class
from documentai_api.mappings.textract import get_supplemental_config
from documentai_api.services import s3 as s3_service
from documentai_api.services.textract import analyze_id
from documentai_api.utils import s3 as s3_utils
from documentai_api.utils.ddb import set_extract_method
from documentai_api.utils.extraction_timing import get_elapsed_time_seconds
from documentai_api.utils.ssm import is_textract_identity_enabled
from documentai_api.utils.textract import (
    extract_fields_from_analyze_id,
    extract_supplemental_fields_via_nova,
    get_id_type,
)

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)


def extract_textract_identity(
    content_type: str,
    file_bytes: bytes,
    ddb_key: str,
) -> ExtractionResult | None:
    """Attempt Textract AnalyzeID extraction.

    Returns an ExtractionResult on success, or None if Textract should not be used
    (flag off, unsupported content type, or Textract failure).
    On failure, logs a warning and returns None so the caller falls through to BDA.
    """
    if not is_textract_identity_enabled():
        return None

    if content_type not in TextractConfig.SUPPORTED_CONTENT_TYPES:
        return None

    try:
        extract_started_at = datetime.now(UTC)
        with tracer.start_as_current_span("textract.analyze_id") as span:
            span.set_attribute("document.content_type", content_type)
            span.set_attribute("document.key", ddb_key)
            textract_response = analyze_id(file_bytes)

        extract_completed_at = datetime.now(UTC)
        id_type = get_id_type(textract_response)
        matched_document_class = get_document_class(id_type)
        field_map = get_bda_field_map(matched_document_class) if matched_document_class else {}

        fields = extract_fields_from_analyze_id(textract_response, field_map)

        if not matched_document_class or not fields:
            logger.info(
                f"Textract could not map document for {ddb_key} "
                f"(id_type={id_type}, class={matched_document_class}, fields={len(fields)}), "
                f"falling back to BDA"
            )
            return None

        supplemental_config = (
            get_supplemental_config(matched_document_class) if matched_document_class else None
        )

        if supplemental_config:
            all_blocks = []

            for doc in textract_response.get("IdentityDocuments", []):
                all_blocks.extend(doc.get("Blocks", []))

            if all_blocks:
                with tracer.start_as_current_span("bedrock.supplemental_extraction") as span:
                    span.set_attribute("document.key", ddb_key)
                    supplemental = extract_supplemental_fields_via_nova(
                        all_blocks, *supplemental_config
                    )
                fields.update(supplemental)

        set_extract_method(ddb_key, ExtractMethod.TEXTRACT, extract_started_at.isoformat())
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

        return ExtractionResult(
            document_type=matched_document_class,
            output_uri=textract_s3_uri,
            extract_started_at=extract_started_at,
            extract_completed_at=extract_completed_at,
            extract_time=extract_time,
            field_confidence_scores=field_confidence_scores,
            field_empty_list=field_empty_list,
        )

    except Exception as e:
        logger.warning(f"Textract AnalyzeID failed for {ddb_key}, falling back to BDA: {e}")
        return None
