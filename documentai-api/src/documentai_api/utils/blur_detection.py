"""Blur detection using Textract OCR confidence scores.

Uses detect_document_text word confidence with quadrant-based spatial
analysis. If any populated quadrant has too many low-confidence words
or low average confidence, the document is flagged as blurry.

For empty quadrants (0 words) on otherwise text-heavy documents, a
fallback LLM vision call determines whether the region contains text
that blur destroyed vs. legitimately non-text content (logos, photos).
"""

import re
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from opentelemetry import trace

from documentai_api.config.constants import ConfigDefaults
from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger
from documentai_api.services.textract import get_words
from documentai_api.utils.ssm import get_parameter_value

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class BlurResult:
    is_blurry: bool
    is_not_document: bool = False
    analysis_failed: bool = False
    avg_confidence: float | None = None
    word_count: int | None = None
    low_confidence_percent: float | None = None
    llm_checked: bool = False
    quadrant_stats: dict[str, Any] | None = None
    blur_reason_text: str | None = None
    duration_seconds: Decimal | None = None


_EMPTY_QUADRANT_PROMPT = (
    "This cropped region is from a document that has dense text in other areas, "
    "but OCR detected NO text in this region. "
    "Does this region contain:"
    "\n- Blurred, smeared, or distorted content that was likely text"
    "\n- Faded or washed-out text remnants"
    "\n- Any visual evidence that text existed but is now unreadable"
    "\n"
    "\nDo NOT answer YES for: blank/white space, photos, logos, barcodes, "
    "or decorative graphics."
    "\n"
    "\nRespond with ONLY YES or NO."
)

# Quadrant crop boundaries as (left, upper, right, lower) fractions of image dimensions
_QUADRANT_CROPS = {
    "top_left": (0.0, 0.0, 0.5, 0.5),
    "top_right": (0.5, 0.0, 1.0, 0.5),
    "bottom_left": (0.0, 0.5, 0.5, 1.0),
    "bottom_right": (0.5, 0.5, 1.0, 1.0),
}


def _check_quadrant(
    words: list[dict[str, Any]],
    confidence_floor: float,
    max_low_pct: float,
    min_avg_confidence: float,
) -> bool:
    """Return True if a populated quadrant is blurry (high low-confidence % or low avg)."""
    confidences = [w["Confidence"] for w in words]
    avg = sum(confidences) / len(confidences)

    if avg < min_avg_confidence:
        return True

    low = sum(1 for c in confidences if c < confidence_floor)

    return (low / len(words)) * 100 > max_low_pct


# Regex to extract YES/NO from LLM output (single quadrant per call now).
# Tolerant of markdown fences, stray text - same lesson as _parse_bbox in bedrock.py.
_YES_NO_RE = re.compile(r"\b(YES|NO)\b", re.IGNORECASE)


def _crop_quadrant(image_bytes: bytes, quadrant_name: str) -> tuple[bytes, str]:
    """Crop a quadrant from the image and return as JPEG bytes + format."""
    import io

    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes))
    left_frac, top_frac, right_frac, bottom_frac = _QUADRANT_CROPS[quadrant_name]
    box = (
        int(left_frac * img.width),
        int(top_frac * img.height),
        int(right_frac * img.width),
        int(bottom_frac * img.height),
    )
    cropped = img.crop(box).convert("RGB")
    output = io.BytesIO()
    cropped.save(output, format="JPEG", quality=85)
    return output.getvalue(), "jpeg"


def _get_blur_quadrant_model_id() -> str:
    param_name = get_aws_config().bedrock_blur_quadrant_model_id_param
    if not param_name:
        return ConfigDefaults.BLUR_QUADRANT_MODEL_ID
    return get_parameter_value(param_name, default=ConfigDefaults.BLUR_QUADRANT_MODEL_ID)


def _check_empty_quadrants_for_text(
    image_bytes: bytes, quadrant_names: list[str]
) -> dict[str, bool]:
    """Ask the LLM which empty quadrants contain blurred/smeared former text.

    Crops each quadrant and sends it individually for reliable spatial grounding.
    Uses _downscale_for_detection on the crop to handle Converse size limits.
    Parses response with regex (not json.loads) to tolerate malformed output.
    """
    from documentai_api.services.bedrock import invoke_model
    from documentai_api.utils.bbox_detection import _downscale_for_detection

    model_id = _get_blur_quadrant_model_id()
    results: dict[str, bool] = {}

    for name in quadrant_names:
        try:
            crop_bytes, crop_fmt = _crop_quadrant(image_bytes, name)
            # Downscale if needed (unlikely for a quarter-image, but safe)
            detection_bytes, fmt = _downscale_for_detection(crop_bytes, f"image/{crop_fmt}")

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"image": {"format": fmt, "source": {"bytes": detection_bytes}}},
                        {"text": _EMPTY_QUADRANT_PROMPT},
                    ],
                }
            ]

            response = invoke_model(
                messages=messages,
                max_tokens=8,
                model_id=model_id,
                temperature=0.0,
            )
            text = response["output"]["message"]["content"][0]["text"]
            match = _YES_NO_RE.search(text)
            results[name] = match.group(1).upper() == "YES" if match else False
        except Exception as e:
            logger.warning(f"Empty quadrant LLM check failed for {name}: {e}")
            results[name] = False

    return results


def _partition_words_into_quadrants(words: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    quadrants: dict[str, list[dict[str, Any]]] = {
        "top_left": [],
        "top_right": [],
        "bottom_left": [],
        "bottom_right": [],
    }

    for w in words:
        bbox = w["Geometry"]["BoundingBox"]
        key = (
            ("top" if bbox["Top"] < 0.5 else "bottom")
            + "_"
            + ("left" if bbox["Left"] < 0.5 else "right")
        )
        quadrants[key].append(w)

    return quadrants


def _evaluate_quadrants(
    quadrants: dict[str, list[dict[str, Any]]],
    confidence_floor: float,
    max_low_pct: float,
    min_avg_confidence: float,
    min_word_count: int,
) -> tuple[list[str], dict[str, Any], str | None]:
    """Evaluate populated quadrants for blur. Returns (failed_quadrants, quadrant_stats, blur_reason_text)."""
    failed_quadrants: list[str] = []
    quadrant_stats: dict[str, Any] = {}
    blur_reason_text: str | None = None

    for name, qwords in quadrants.items():
        if len(qwords) >= min_word_count:
            q_confidences = [w["Confidence"] for w in qwords]
            q_avg = sum(q_confidences) / len(q_confidences)
            q_low_pct = (sum(1 for c in q_confidences if c < confidence_floor) / len(qwords)) * 100
            quadrant_stats[name] = {
                "word_count": len(qwords),
                "avg_confidence": round(q_avg, 1),
                "low_confidence_percent": round(q_low_pct, 1),
            }
            if _check_quadrant(qwords, confidence_floor, max_low_pct, min_avg_confidence):
                failed_quadrants.append(name)
                if q_avg < min_avg_confidence:
                    blur_reason_text = (
                        f"OCR confidence in the {name.replace('_', ' ')} quadrant averaged "
                        f"{q_avg:.2f}%. The value did not meet the minimum required {min_avg_confidence:.2f}%."
                    )
                else:
                    blur_reason_text = (
                        f"{q_low_pct:.2f}% of words in the {name.replace('_', ' ')} quadrant "
                        f"were low-confidence. The value exceeded the allowed {max_low_pct:.2f}%."
                    )
                break
        else:
            quadrant_stats[name] = {
                "word_count": len(qwords),
                "avg_confidence": 0.0,
                "low_confidence_percent": 0.0,
                "skipped": True,
            }

    return failed_quadrants, quadrant_stats, blur_reason_text


def _page_fallback_result(
    avg_confidence: float,
    low_confidence_percent: float,
    min_avg_confidence: float,
    max_low_confidence_percent: float,
) -> tuple[bool, str | None]:
    """Whole-page fallback when all quadrants were skipped. Returns (is_blurry, blur_reason_text)."""
    if avg_confidence < min_avg_confidence:
        return True, (
            f"OCR confidence averaged {avg_confidence:.2f}% across all words. "
            f"The value did not meet the minimum required {min_avg_confidence:.2f}%."
        )

    if low_confidence_percent > max_low_confidence_percent:
        return True, (
            f"{low_confidence_percent:.2f}% of all words were low-confidence. "
            f"The value exceeded the allowed {max_low_confidence_percent:.2f}%."
        )

    return False, None


def detect_blur(image_bytes: bytes, content_type: str | None = None) -> BlurResult:
    """Detect blur using Textract OCR word confidence scores with quadrant analysis.

    Only runs on images. PDFs and other content types are skipped (returns not blurry).

    Args:
        image_bytes: Image bytes to analyze.
        content_type: MIME type. Non-image types are skipped.

    Returns:
        BlurResult with detection outcomes.
    """
    if not content_type:
        content_type = "image/jpeg"

    if not content_type.startswith("image/"):
        return BlurResult(
            is_blurry=False, blur_reason_text="Blur check not performed - document is not an image."
        )

    confidence_floor = ConfigDefaults.BLUR_CONFIDENCE_FLOOR
    min_word_count = ConfigDefaults.BLUR_MIN_WORD_COUNT
    max_low_confidence_percent = ConfigDefaults.BLUR_LOW_CONFIDENCE_MAX_PERCENT
    min_avg_confidence = ConfigDefaults.BLUR_QUADRANT_MIN_AVG_CONFIDENCE

    try:
        start = time.time()
        with tracer.start_as_current_span("textract.detect_document_text") as span:
            span.set_attribute("document.content_type", content_type)
            words = get_words(image_bytes)
        elapsed = round(time.time() - start, 2)

        word_count = len(words)

        if word_count < min_word_count:
            return BlurResult(
                is_blurry=False,
                is_not_document=True,
                avg_confidence=0.0,
                word_count=word_count,
                blur_reason_text="Insufficient text detected to identify a document.",
                duration_seconds=Decimal(str(elapsed)),
            )

        quadrants = _partition_words_into_quadrants(words)
        failed_quadrants, quadrant_stats, blur_reason_text = _evaluate_quadrants(
            quadrants,
            confidence_floor,
            max_low_confidence_percent,
            min_avg_confidence,
            min_word_count,
        )

        # For empty quadrants on text-dense documents, ask the LLM whether blur
        # destroyed text in that region. Skip if confidence check already failed.
        llm_checked = False

        if not failed_quadrants:
            empty_quadrant_names = [
                name
                for name, qwords in quadrants.items()
                if len(qwords) == 0 and word_count >= ConfigDefaults.BLUR_TEXT_DENSE_MIN_WORDS
            ]
            if empty_quadrant_names:
                llm_results = _check_empty_quadrants_for_text(image_bytes, empty_quadrant_names)
                llm_checked = True
                for name, has_text in llm_results.items():
                    quadrant_stats[name] = {
                        "word_count": 0,
                        "avg_confidence": 0.0,
                        "low_confidence_percent": 0.0,
                        "skipped": False,
                        "is_text_detected_by_llm": has_text,
                    }
                    if has_text:
                        failed_quadrants.append(name)
                        blur_reason_text = (
                            f"OCR did not detect any words in the {name.replace('_', ' ')} quadrant; "
                            f"an LLM confirmed the region contained blurred or unreadable text."
                        )

        confidences = [w["Confidence"] for w in words]
        avg_confidence = sum(confidences) / len(confidences)
        low_confidence_percent = (
            sum(1 for c in confidences if c < confidence_floor) / word_count
        ) * 100

        all_quadrants_skipped = all(q.get("skipped", False) for q in quadrant_stats.values())

        if failed_quadrants:
            is_blurry = True
        elif all_quadrants_skipped:
            is_blurry, blur_reason_text = _page_fallback_result(
                avg_confidence,
                low_confidence_percent,
                min_avg_confidence,
                max_low_confidence_percent,
            )
        else:
            is_blurry = False
            blur_reason_text = "No blur indicators detected."

        logger.info(
            "Blur detection complete",
            extra={
                "is_blurry": is_blurry,
                "avg_confidence": round(avg_confidence, 1),
                "word_count": word_count,
                "low_confidence_percent": round(low_confidence_percent, 1),
                "failed_quadrants": failed_quadrants,
            },
        )

        return BlurResult(
            is_blurry=is_blurry,
            avg_confidence=avg_confidence,
            word_count=word_count,
            low_confidence_percent=low_confidence_percent,
            llm_checked=llm_checked,
            quadrant_stats=quadrant_stats,
            blur_reason_text=blur_reason_text,
            duration_seconds=Decimal(str(elapsed)),
        )

    except Exception as e:
        logger.warning(f"Blur detection failed: {e}")
        return BlurResult(
            is_blurry=False, analysis_failed=True, blur_reason_text="Blur analysis failed."
        )
