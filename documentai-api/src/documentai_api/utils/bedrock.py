import io
import json
import re
import time
from typing import Any

from PIL import Image

from documentai_api.config.constants import (
    ConfigDefaults,
    PreclassificationCategory,
    PreClassificationDefaults,
    PreprocessingBoundingBoxDefault,
)
from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger
from documentai_api.services.bedrock import invoke_model
from documentai_api.utils.dto import BedrockClassificationResult
from documentai_api.utils.ssm import get_parameter_value

logger = get_logger(__name__)

DEFAULT_PRECLASSIFICATION_MODEL_ID = PreClassificationDefaults.MODEL_ID
DEFAULT_PRECLASSIFICATION_PROMPT = PreClassificationDefaults.PROMPT
SUPPORTED_CLASSIFICATION_TYPES = PreClassificationDefaults.SUPPORTED_CONTENT_TYPES
DEFAULT_BOUNDING_BOX_MODEL_ID = PreprocessingBoundingBoxDefault.MODEL_ID


def _get_model_id() -> str:
    param_name = get_aws_config().bedrock_classification_model_id_param
    if not param_name:
        return DEFAULT_PRECLASSIFICATION_MODEL_ID
    return get_parameter_value(param_name, default=DEFAULT_PRECLASSIFICATION_MODEL_ID)


def _get_bbox_model_id() -> str:
    param_name = get_aws_config().bedrock_bounding_box_model_id_param
    if not param_name:
        return DEFAULT_BOUNDING_BOX_MODEL_ID
    return get_parameter_value(param_name, default=DEFAULT_BOUNDING_BOX_MODEL_ID)


def _get_classification_prompt() -> str:
    param_name = get_aws_config().bedrock_classification_prompt_param
    if not param_name:
        return DEFAULT_PRECLASSIFICATION_PROMPT
    return get_parameter_value(param_name, default=DEFAULT_PRECLASSIFICATION_PROMPT)


def _invoke(messages: list[Any], max_tokens: int = 256, model_id: str | None = None) -> Any:
    if model_id is None:
        model_id = _get_model_id()
    logger.info(f"Invoking Bedrock model: {model_id}")
    return invoke_model(model_id=model_id, messages=messages, max_tokens=max_tokens)


def _parse_bbox(text: str) -> tuple[float, float, float, float] | None:
    """Extract a 4-number bounding box from the model's text response.

    Tolerant of the malformed JSON vision models routinely emit (markdown fences,
    stray brackets, missing braces): pulls the four ``bounding_box`` numbers via
    regex rather than ``json.loads``. Returns ``None`` for an explicit null box.
    """
    if re.search(r"bounding_box\"?\s*:\s*null", text):
        return None
    match = PreprocessingBoundingBoxDefault.ARRAY_RE.search(text)
    if not match:
        return None
    return tuple(float(v) for v in match.groups())  # type: ignore[return-value]


def _downscale_for_detection(image_bytes: bytes, content_type: str) -> tuple[bytes, str]:
    """Return image bytes and format within the Bedrock Converse per-image limits.

    The Converse API rejects images over 3.75MB or 8000px on a side - stricter than
    the 5MB BDA limit - so large phone photos (the ones most in need of cropping)
    would otherwise be skipped. We downscale an in-memory copy *only for the Nova
    call*: the returned bbox is on a normalized 0-1000 scale, so it still applies to
    the full-resolution original via ``crop_image_to_bbox``.

    Best-effort: returns ``(image_bytes, <source format>)`` unchanged if it is already
    within limits or if downscaling fails.
    """
    fmt = content_type.split("/")[1]
    max_bytes = int(ConfigDefaults.BEDROCK_CONVERSE_MAX_IMAGE_BYTES)
    max_dim = int(ConfigDefaults.BEDROCK_CONVERSE_MAX_IMAGE_DIMENSION_PX)

    try:
        img = Image.open(io.BytesIO(image_bytes))
        if len(image_bytes) <= max_bytes and max(img.size) <= max_dim:
            return image_bytes, fmt

        img = img.convert("RGB")

        # Cap the longest side first, then re-encode as JPEG, stepping quality down and
        # halving dimensions as needed until the encoded bytes fit under the limit.
        if max(img.size) > max_dim:
            scale = max_dim / max(img.size)
            img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))))

        downscaled = b""
        for quality in (85, 70, 55, 40):
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=quality)
            downscaled = output.getvalue()
            if len(downscaled) <= max_bytes:
                break
        else:
            # quality floor still too large: keep halving dimensions at quality 40
            while len(downscaled) > max_bytes and min(img.size) > 2:
                img = img.resize((max(1, img.width // 2), max(1, img.height // 2)))
                output = io.BytesIO()
                img.save(output, format="JPEG", quality=40)
                downscaled = output.getvalue()

        logger.info(
            "Downscaled image for bbox detection",
            extra={"original_bytes": len(image_bytes), "detection_bytes": len(downscaled)},
        )
        return downscaled, "jpeg"
    except Exception as e:
        logger.warning(f"Could not downscale image for bbox detection: {e}")
        return image_bytes, fmt


def detect_document_bbox(
    image_bytes: bytes, content_type: str
) -> tuple[float, float, float, float] | None:
    """Detect the primary document's bounding box in an image via the Bedrock vision model.

    Returns the box as ``(x1, y1, x2, y2)`` on Nova's 0-1000 normalized scale, or
    ``None`` when no document is found or detection fails. Best-effort - never raises.

    Images above the Bedrock Converse per-image limits are downscaled in-memory just
    for this call; the normalized box still maps onto the full-resolution original.
    """
    if not content_type.startswith("image/"):
        return None

    detection_bytes, detection_format = _downscale_for_detection(image_bytes, content_type)

    messages = [
        {
            "role": "user",
            "content": [
                {"image": {"format": detection_format, "source": {"bytes": detection_bytes}}},
                {"text": PreprocessingBoundingBoxDefault.PROMPT},
            ],
        }
    ]

    try:
        result = _invoke(messages=messages, model_id=_get_bbox_model_id())
        box = _parse_bbox(result["content"][0]["text"])
        if box is None:
            return None

        x1, y1, x2, y2 = box
        # reject degenerate / out-of-range boxes
        if not (0 <= x1 < x2 <= 1000 and 0 <= y1 < y2 <= 1000):
            logger.warning(f"Ignoring invalid document bbox: {box}")
            return None

        return x1, y1, x2, y2
    except Exception as e:
        logger.warning(f"Document bbox detection failed: {e}")
        return None


def preclassify_document(document_bytes: bytes, content_type: str) -> BedrockClassificationResult:
    """Classify document type and count using Bedrock vision model."""
    if content_type not in SUPPORTED_CLASSIFICATION_TYPES:
        logger.info(f"Unsupported content type for classification: {content_type}")
        return BedrockClassificationResult(
            document_type="other_document", confidence=0.0, document_count=1, is_document=True
        )

    if content_type.startswith("image/") and len(document_bytes) > int(
        ConfigDefaults.BDA_MAX_IMAGE_SIZE_BYTES
    ):
        logger.info("Image exceeds 5MB, skipping classification")
        return BedrockClassificationResult(
            document_type="other_document", confidence=0.0, document_count=1, is_document=True
        )

    prompt = _get_classification_prompt()

    if content_type == "application/pdf":
        content_block = {
            "document": {"format": "pdf", "name": "document", "source": {"bytes": document_bytes}}
        }
    else:
        content_block = {
            "image": {"format": content_type.split("/")[1], "source": {"bytes": document_bytes}}
        }

    messages = [
        {
            "role": "user",
            "content": [content_block, {"text": prompt}],
        }
    ]

    try:
        start = time.time()
        result = _invoke(messages=messages)
        elapsed = round(time.time() - start, 2)

        text = result["content"][0]["text"]
        parsed = json.loads(text)

        document_type = parsed.get("document_type", "other_document")
        valid_types = [e.value for e in PreclassificationCategory] + ["other_document"]
        if document_type not in valid_types:
            document_type = "other_document"

        classification = BedrockClassificationResult(
            document_type=document_type,
            confidence=max(0.0, min(1.0, float(parsed.get("confidence", 0.0)))),
            document_count=max(0, int(parsed.get("document_count", 1))),
            is_document=str(parsed.get("is_document", True)).lower() == "true",
            is_blurry=str(parsed.get("is_blurry", False)).lower() == "true",
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
