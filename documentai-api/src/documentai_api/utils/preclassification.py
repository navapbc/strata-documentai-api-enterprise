"""Document preclassification using Bedrock vision models."""

import time
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from documentai_api.config.constants import (
    ConfigDefaults,
    PreclassificationCategory,
    PreClassificationDefaults,
)
from documentai_api.config.env import get_aws_config
from documentai_api.dtos.classification import (
    BedrockClassificationResult,
    PreclassificationMatchResult,
)
from documentai_api.logging import get_logger
from documentai_api.services.bedrock import invoke_model
from documentai_api.utils.ssm import get_parameter_value

logger = get_logger(__name__)

SUPPORTED_CLASSIFICATION_TYPES = PreClassificationDefaults.SUPPORTED_CONTENT_TYPES


class _PreclassificationResponse(BaseModel):
    """Expected shape of the Bedrock vision classifier's JSON output.

    Fields default so a partial or malformed response yields a safe result.
    """

    model_config = ConfigDict(extra="ignore")

    document_type: str = "other_document"
    confidence: float = 0.0
    document_count: int = 1


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


def _get_classification_prompt() -> str:
    param_name = get_aws_config().bedrock_classification_prompt_param
    if not param_name:
        return PreClassificationDefaults.PROMPT
    return get_parameter_value(param_name, default=PreClassificationDefaults.PROMPT)


def _build_content_block(document_bytes: bytes, content_type: str) -> dict[str, Any]:
    """Build the Converse API content block for a document or image."""
    if content_type == "application/pdf":
        return {
            "document": {"format": "pdf", "name": "document", "source": {"bytes": document_bytes}}
        }
    return {"image": {"format": content_type.split("/")[1], "source": {"bytes": document_bytes}}}


def preclassify_document(document_bytes: bytes, content_type: str) -> BedrockClassificationResult:
    """Classify document type and count using Bedrock vision model."""
    if content_type not in SUPPORTED_CLASSIFICATION_TYPES:
        logger.info(f"Unsupported content type for classification: {content_type}")
        return BedrockClassificationResult(
            document_type="other_document", confidence=0.0, document_count=1
        )

    if content_type.startswith("image/") and len(document_bytes) > int(
        ConfigDefaults.BDA_MAX_IMAGE_SIZE_BYTES
    ):
        logger.info("Image exceeds 5MB, skipping classification")
        return BedrockClassificationResult(
            document_type="other_document", confidence=0.0, document_count=1
        )

    prompt = _get_classification_prompt()
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
        response = invoke_model(messages=messages, model_id=model_id)
        elapsed = round(time.time() - start, 2)

        usage = response.get("usage", {})
        text = response["output"]["message"]["content"][0]["text"]

        try:
            parsed = _PreclassificationResponse.model_validate_json(text)
        except ValidationError as e:
            logger.warning(f"Bedrock classification returned output failing schema validation: {e}")
            return BedrockClassificationResult(
                document_type="other_document", confidence=0.0, document_count=1
            )

        document_type = parsed.document_type
        valid_types = [e.value for e in PreclassificationCategory] + ["other_document"]
        if document_type not in valid_types:
            document_type = "other_document"

        classification = BedrockClassificationResult(
            document_type=document_type,
            confidence=max(0.0, min(1.0, parsed.confidence)),
            document_count=max(0, parsed.document_count),
            input_tokens=usage.get("inputTokens"),
            output_tokens=usage.get("outputTokens"),
            duration_seconds=Decimal(str(elapsed)),
            model_id=model_id,
        )

        logger.info(
            f"Pre-classification complete in {elapsed}s: "
            f"type={classification.document_type}, "
            f"confidence={classification.confidence}, "
            f"document_count={classification.document_count}"
        )

        return classification
    except Exception as e:
        logger.warning(f"Document classification failed: {e}")
        return BedrockClassificationResult(
            document_type="other_document", confidence=0.0, document_count=1
        )


def _build_blueprint_prompt(schemas: dict[str, Any]) -> str:
    """Build a prompt listing all blueprints for the model to evaluate against."""
    lines = [
        "You are an expert document classification system.",
        "Analyze the provided document and classify it into EXACTLY ONE of the following categories.",
        "",
        "Respond in JSON only:",
        '{"matched_blueprint": "class_name_or_OTHER", "confidence": float 0-1}',
        "",
        "Categories:",
        "",
    ]

    for doc_type, schema in schemas.items():
        desc = schema.get("description", "")
        if desc:
            lines.append(f"- {doc_type}: {desc}")
        else:
            lines.append(f"- {doc_type}")
        fields = schema.get("fields", [])
        if fields:
            field_names = ", ".join(f["name"] for f in fields)
            lines.append(f"  Fields: {field_names}")

    lines.append("")
    lines.append("OTHER: Use this ONLY if the document does not fit any of the above categories.")
    lines.append("")
    lines.append("You MUST pick exactly one. Use OTHER if uncertain.")

    return "\n".join(lines)


def find_matching_blueprint(
    document_bytes: bytes, content_type: str, category: str | None = None
) -> PreclassificationMatchResult:
    """Match a document against available BDA blueprints.

    Called after preclassification to identify which specific blueprint the document
    matches. Result is stored for observability - no routing decisions are made from it.

    Gated by the enable-preclassification-blueprint-matching SSM flag (default true).
    Returns an empty result when disabled.

    If category is provided, only blueprints in that category are considered.
    """
    config = get_aws_config()
    if config.ssm_prefix:
        param = f"{config.ssm_prefix}/feature-flags/enable-preclassification-blueprint-matching"
        value = get_parameter_value(param, default="true")
        if value.lower() != "true":
            return PreclassificationMatchResult()

    from documentai_api.utils.schemas import get_all_schemas

    all_schemas = get_all_schemas()
    if category:
        filtered = {k: v for k, v in all_schemas.items() if v.get("category") == category}
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
        if matched and (matched == "OTHER" or matched not in schemas):
            matched = None

        # Confidence threshold: reject weak matches
        if matched and parsed.confidence < 0.5:
            logger.info(
                f"Blueprint match '{matched}' rejected: confidence {parsed.confidence} below threshold"
            )
            matched = None

        matched_schema = schemas.get(matched, {}) if matched else {}
        return PreclassificationMatchResult(
            matched_document_type=matched,
            confidence=max(0.0, min(1.0, parsed.confidence)),
            category=matched_schema.get("category"),
            input_tokens=usage.get("inputTokens"),
            output_tokens=usage.get("outputTokens"),
            duration_seconds=Decimal(str(elapsed)),
        )
    except Exception as e:
        logger.warning(f"Blueprint matching failed: {e}")
        return PreclassificationMatchResult()
