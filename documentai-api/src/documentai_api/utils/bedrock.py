import json
import os
import time
from typing import Any

from documentai_api.config.constants import (
    ConfigDefaults,
    PreClassificationDefaults,
)
from documentai_api.logging import get_logger
from documentai_api.services.bedrock import invoke_model
from documentai_api.utils.env import (
    BEDROCK_CLASSIFICATION_MODEL_ID_PARAM,
    BEDROCK_CLASSIFICATION_PROMPT_PARAM,
)
from documentai_api.utils.models import BedrockClassificationResult
from documentai_api.utils.ssm import get_parameter_value

logger = get_logger(__name__)

DEFAULT_PRECLASSIFICATION_MODEL_ID = PreClassificationDefaults.MODEL_ID
DEFAULT_PRECLASSIFICATION_PROMPT = PreClassificationDefaults.PROMPT


def _get_model_id() -> str:
    param_name = os.getenv(BEDROCK_CLASSIFICATION_MODEL_ID_PARAM)
    if not param_name:
        return DEFAULT_PRECLASSIFICATION_MODEL_ID
    return get_parameter_value(param_name, default=DEFAULT_PRECLASSIFICATION_MODEL_ID)


def _get_classification_prompt(document_types: list[str]) -> str:
    param_name = os.getenv(BEDROCK_CLASSIFICATION_PROMPT_PARAM)
    if not param_name:
        template = DEFAULT_PRECLASSIFICATION_PROMPT
    else:
        template = get_parameter_value(param_name, default=DEFAULT_PRECLASSIFICATION_PROMPT)
    return template.replace("<<DOCUMENT_TYPES>>", json.dumps(document_types))


def _invoke(messages: list[Any], max_tokens: int = 256) -> Any:
    model_id = _get_model_id()
    logger.info(f"Invoking Bedrock model: {model_id}")
    return invoke_model(model_id=model_id, messages=messages, max_tokens=max_tokens)


def preclassify_document_image(
    image_bytes: bytes, content_type: str, document_types: list[str]
) -> BedrockClassificationResult:
    """Classify document type and count using Bedrock vision model."""
    if not content_type.startswith("image/"):
        logger.info(f"Non-image content type, skipping classification: {content_type}")
        return BedrockClassificationResult(
            document_type="other_document", confidence=0.0, document_count=1, is_document=True
        )

    if len(image_bytes) > int(ConfigDefaults.BDA_MAX_IMAGE_SIZE_BYTES):
        logger.info("Image exceeds 5MB, skipping classification")
        return BedrockClassificationResult(
            document_type="other_document", confidence=0.0, document_count=1, is_document=True
        )

    prompt = _get_classification_prompt(document_types)
    messages = [
        {
            "role": "user",
            "content": [
                {"image": {"format": content_type.split("/")[1], "source": {"bytes": image_bytes}}},
                {"text": prompt},
            ],
        }
    ]

    try:
        start = time.time()
        result = _invoke(messages=messages)
        elapsed = round(time.time() - start, 2)

        text = result["content"][0]["text"]
        parsed = json.loads(text)

        document_type = parsed.get("document_type", "other_document")
        valid_types = [*document_types, "other_document", "not_a_document"]
        if document_type not in valid_types:
            document_type = "other_document"

        classification = BedrockClassificationResult(
            document_type=document_type,
            confidence=parsed.get("confidence", 0.0),
            document_count=parsed.get("document_count", 1),
            is_document=parsed.get("is_document", True),
            is_blurry=parsed.get("is_blurry", False),
        )

        logger.info(
            f"Pre-classification complete in {elapsed}s: "
            f"type={classification.document_type}, "
            f"confidence={classification.confidence}, "
            f"document_count={classification.document_count}, "
            f"is_document={classification.is_document}"
        )

        return classification
    except Exception as e:
        logger.warning(f"Document classification failed: {e}")
        return BedrockClassificationResult(
            document_type="other_document", confidence=0.0, document_count=1, is_document=True
        )
