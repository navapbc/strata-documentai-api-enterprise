"""Document bounding-box detection via Bedrock vision models."""

import io
import re
import time
from decimal import Decimal

from PIL import Image

from documentai_api.config.constants import (
    ConfigDefaults,
    PreprocessingBoundingBoxDefault,
)
from documentai_api.config.env import get_aws_config
from documentai_api.dtos.processing import CropResult
from documentai_api.logging import get_logger
from documentai_api.services.bedrock import invoke_model
from documentai_api.utils.ssm import get_parameter_value

logger = get_logger(__name__)


def _get_bbox_model_id() -> str:
    param_name = get_aws_config().bedrock_bounding_box_model_id_param
    if not param_name:
        return PreprocessingBoundingBoxDefault.MODEL_ID
    return get_parameter_value(param_name, default=PreprocessingBoundingBoxDefault.MODEL_ID)


def _parse_bbox(text: str) -> tuple[float, float, float, float] | None:
    """Extract a 4-number bounding box from the model's text response."""
    if re.search(r"bounding_box\"?\s*:\s*null", text):
        return None
    match = PreprocessingBoundingBoxDefault.ARRAY_RE.search(text)
    if not match:
        return None
    return tuple(float(v) for v in match.groups())  # type: ignore[return-value]


def _downscale_for_detection(image_bytes: bytes, content_type: str) -> tuple[bytes, str]:
    """Return image bytes and format within Bedrock Converse per-image limits.

    Downscales an in-memory copy only for the detection call; the returned bbox
    is on a normalized 0-1000 scale so it applies to the full-resolution original.
    """
    fmt = content_type.split("/")[1]
    max_bytes = int(ConfigDefaults.BEDROCK_CONVERSE_MAX_IMAGE_BYTES)
    max_dim = int(ConfigDefaults.BEDROCK_CONVERSE_MAX_IMAGE_DIMENSION_PX)

    try:
        img = Image.open(io.BytesIO(image_bytes))
        if len(image_bytes) <= max_bytes and max(img.size) <= max_dim:
            return image_bytes, fmt

        img = img.convert("RGB")

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
) -> tuple[tuple[float, float, float, float] | None, CropResult]:
    """Detect the primary document's bounding box in an image via Bedrock vision model."""
    result = CropResult()

    if not content_type.startswith("image/"):
        return None, result

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
        model_id = _get_bbox_model_id()
        start = time.time()
        response = invoke_model(messages=messages, model_id=model_id)
        elapsed = round(time.time() - start, 2)

        usage = response.get("usage", {})
        result.duration_seconds = Decimal(str(elapsed))
        result.input_tokens = usage.get("inputTokens")
        result.output_tokens = usage.get("outputTokens")
        result.model_id = model_id

        text = response["output"]["message"]["content"][0]["text"]
        box = _parse_bbox(text)
        if box is None:
            return None, result

        x1, y1, x2, y2 = box
        if not (0 <= x1 < x2 <= 1000 and 0 <= y1 < y2 <= 1000):
            logger.warning(f"Ignoring invalid document bbox: {box}")
            return None, result

        return (x1, y1, x2, y2), result
    except Exception as e:
        logger.warning(f"Document bbox detection failed: {e}")
        return None, result
