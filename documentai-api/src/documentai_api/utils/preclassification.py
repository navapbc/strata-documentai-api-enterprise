"""Document preclassification using Bedrock vision models."""

import re
import time
from decimal import Decimal
from typing import Any

from opentelemetry import trace
from pydantic import BaseModel, ConfigDict, ValidationError

from documentai_api.config.constants import (
    ConfigDefaults,
    PreClassificationDefaults,
)
from documentai_api.config.env import get_aws_config
from documentai_api.dtos.classification import (
    BedrockClassificationResult,
    PreclassificationMatchResult,
)
from documentai_api.logging import get_logger
from documentai_api.services.bedrock import invoke_model
from documentai_api.utils.schemas import DocumentSchema
from documentai_api.utils.ssm import get_parameter_value

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)

SUPPORTED_CLASSIFICATION_TYPES = PreClassificationDefaults.SUPPORTED_CONTENT_TYPES


class _PreclassificationResponse(BaseModel):
    """Expected shape of the Bedrock vision classifier's JSON output.

    Fields default so a partial or malformed response yields a safe result.
    """

    model_config = ConfigDict(extra="ignore")

    document_type: str = "other_document"
    confidence: float = 0.0
    max_document_count_on_page: int = 1
    max_document_count_on_page_reason: str = ""
    has_multipage_inconsistency: bool = False
    has_multipage_inconsistency_reason: str = ""
    category_match: bool = True
    is_identity_document: bool = False


class _BlueprintMatchResponse(BaseModel):
    """Expected shape of the blueprint matching model's JSON output."""

    model_config = ConfigDict(extra="ignore")

    matched_blueprint: str | None = None
    confidence: float = 0.0


def _get_model_id() -> str:
    param_name = get_aws_config().bedrock_classification_model_id_param
    if not param_name:
        return PreClassificationDefaults.MODEL_ID
    return get_parameter_value(param_name, default=PreClassificationDefaults.MODEL_ID)


def _build_content_block(document_bytes: bytes, content_type: str) -> dict[str, Any]:
    """Build the Converse API content block for a document or image."""
    if content_type == "application/pdf":
        return {
            "document": {"format": "pdf", "name": "document", "source": {"bytes": document_bytes}}
        }
    return {"image": {"format": content_type.split("/")[1], "source": {"bytes": document_bytes}}}


def _sanitize_category(user_category: str | None) -> str:
    """Strip characters that could break out of the prompt template."""
    if not user_category:
        return "unknown"
    return re.sub(r"[^a-z0-9 _-]", " ", user_category.lower()).strip() or "unknown"


def preclassify_document(
    document_bytes: bytes, content_type: str, user_category: str | None = None
) -> BedrockClassificationResult:
    """Classify document type and count using Bedrock vision model."""
    if content_type not in SUPPORTED_CLASSIFICATION_TYPES:
        logger.info(f"Unsupported content type for classification: {content_type}")
        return BedrockClassificationResult(
            document_type="other_document", confidence=0.0, max_document_count_on_page=1
        )

    if content_type.startswith("image/") and len(document_bytes) > int(
        ConfigDefaults.BDA_MAX_IMAGE_SIZE_BYTES
    ):
        logger.info("Image exceeds 5MB, skipping classification")
        return BedrockClassificationResult(
            document_type="other_document", confidence=0.0, max_document_count_on_page=1
        )

    prompt = PreClassificationDefaults.PROMPT.replace(
        "{user_category}", _sanitize_category(user_category)
    )
    content_block = _build_content_block(document_bytes, content_type)

    messages = [
        {
            "role": "user",
            "content": [content_block, {"text": prompt}],
        }
    ]

    try:
        model_id = _get_model_id()
        start = time.time()
        with tracer.start_as_current_span("bedrock.preclassify") as span:
            span.set_attribute("bedrock.model_id", model_id)
            span.set_attribute("document.content_type", content_type)
            response = invoke_model(messages=messages, model_id=model_id)
        elapsed = round(time.time() - start, 2)

        usage = response.get("usage", {})
        text = response["output"]["message"]["content"][0]["text"]

        try:
            parsed = _PreclassificationResponse.model_validate_json(text)
        except ValidationError as e:
            logger.warning(f"Bedrock classification returned output failing schema validation: {e}")
            return BedrockClassificationResult(
                document_type="other_document", confidence=0.0, max_document_count_on_page=1
            )

        document_type = parsed.document_type

        classification = BedrockClassificationResult(
            document_type=document_type,
            confidence=max(0.0, min(1.0, parsed.confidence)),
            max_document_count_on_page=max(0, parsed.max_document_count_on_page),
            max_document_count_on_page_reason=parsed.max_document_count_on_page_reason,
            has_multipage_inconsistency=parsed.has_multipage_inconsistency,
            has_multipage_inconsistency_reason=parsed.has_multipage_inconsistency_reason,
            category_match=parsed.category_match if user_category else None,
            is_identity_document=parsed.is_identity_document,
            input_tokens=usage.get("inputTokens"),
            output_tokens=usage.get("outputTokens"),
            duration_seconds=Decimal(str(elapsed)),
            model_id=model_id,
        )

        logger.info(
            f"Pre-classification complete in {elapsed}s: "
            f"type={classification.document_type}, "
            f"confidence={classification.confidence}, "
            f"max_document_count_on_page={classification.max_document_count_on_page}, "
            f"user_category={user_category}, "
            f"category_match={classification.category_match}"
        )

        return classification
    except Exception as e:
        logger.warning(f"Document classification failed: {e}")
        return BedrockClassificationResult(
            document_type="other_document", confidence=0.0, max_document_count_on_page=1
        )


def _build_blueprint_prompt(schemas: dict[str, DocumentSchema]) -> str:
    """Build a prompt listing all blueprints for the model to evaluate against."""
    lines = [
        "You are an expert document classification system.",
        "",
        "Perform this evaluation step-by-step:",
        "1. Examine the document and the categories listed below.",
        "2. Pick the single category whose description best matches the document.",
        "3. Copy that category's label EXACTLY character-for-character into matched_blueprint -",
        '   the text immediately after "- " and before the colon. Do not paraphrase, translate,',
        "   reformat, or change capitalization, hyphenation, or pluralization.",
        '4. If no category fits, set matched_blueprint to "OTHER".',
        "",
        "Then, output your final answer strictly as a raw JSON object with no markdown formatting or backticks:",
        "{",
        '  "matched_blueprint": "<category label copied exactly, or OTHER>",',
        '  "confidence": <float between 0.0 and 1.0>',
        "}",
        "",
        "Categories:",
        "",
    ]

    for doc_type, schema in schemas.items():
        desc = schema.description
        lines.append(f"- {doc_type}: {desc}" if desc else f"- {doc_type}")

        fields = schema.fields

        if fields:
            field_names = ", ".join(f.name for f in fields)
            lines.append(f"  Fields: {field_names}")

    return "\n".join(lines)


def find_matching_blueprint(
    document_bytes: bytes, content_type: str, category: str | None = None
) -> PreclassificationMatchResult:
    """Match a document against available BDA blueprints.

    Called after preclassification to identify which specific blueprint the document
    matches. The matched category is stored in DDB and, when preclassification routing
    is enabled, drives which BDA project the document is sent to.

    Gated by the enable-preclassification-blueprint-matching SSM flag (default true).
    Returns an empty result when disabled.

    If category is provided, only blueprints in that category are considered.
    """
    from documentai_api.utils.ssm import is_preclassification_blueprint_matching_enabled

    if not is_preclassification_blueprint_matching_enabled():
        return PreclassificationMatchResult()

    from documentai_api.utils.schemas import get_all_schemas

    all_schemas = get_all_schemas()

    if category:
        filtered = {k: v for k, v in all_schemas.items() if v.category == category}
        schemas = filtered or all_schemas
    else:
        schemas = all_schemas

    if not schemas:
        logger.warning("No blueprint schemas available for matching")
        return PreclassificationMatchResult()

    prompt = _build_blueprint_prompt(schemas)
    content_block = _build_content_block(document_bytes, content_type)

    messages = [
        {
            "role": "user",
            "content": [content_block, {"text": prompt}],
        }
    ]

    try:
        model_id = _get_model_id()
        start = time.time()

        with tracer.start_as_current_span("bedrock.blueprint_match") as span:
            span.set_attribute("bedrock.model_id", model_id)
            span.set_attribute("document.content_type", content_type)
            span.set_attribute("blueprint.schema_count", len(schemas))
            response = invoke_model(messages=messages, model_id=model_id, temperature=0.0)

        elapsed = round(time.time() - start, 2)
        usage = response.get("usage", {})
        text = response["output"]["message"]["content"][0]["text"]

        try:
            parsed = _BlueprintMatchResponse.model_validate_json(text)
        except ValidationError as e:
            logger.warning(f"Blueprint matching returned invalid output: {e}")
            return PreclassificationMatchResult(
                input_tokens=usage.get("inputTokens"),
                output_tokens=usage.get("outputTokens"),
                duration_seconds=Decimal(str(elapsed)),
            )

        matched = parsed.matched_blueprint

        if matched and matched == "OTHER":
            logger.info(f"Blueprint match: model returned OTHER (confidence {parsed.confidence})")
            matched = None
        elif matched and matched not in schemas:
            logger.warning(
                f"Blueprint match '{matched}' rejected: not an exact schema key "
                f"(confidence {parsed.confidence}); known keys: {sorted(schemas)}"
            )
            matched = None

        # Confidence threshold: reject weak matches
        if matched and parsed.confidence < 0.5:
            logger.info(
                f"Blueprint match '{matched}' rejected: confidence {parsed.confidence} below threshold"
            )
            matched = None

        matched_schema = schemas.get(matched) if matched else None

        return PreclassificationMatchResult(
            matched_document_type=matched,
            confidence=max(0.0, min(1.0, parsed.confidence)),
            category=matched_schema.category if matched_schema else None,
            input_tokens=usage.get("inputTokens"),
            output_tokens=usage.get("outputTokens"),
            duration_seconds=Decimal(str(elapsed)),
        )
    except Exception as e:
        logger.warning(f"Blueprint matching failed: {e}")
        return PreclassificationMatchResult()
