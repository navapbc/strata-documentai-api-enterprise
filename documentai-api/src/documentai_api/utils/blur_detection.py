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

from documentai_api.logging import get_logger

logger = get_logger(__name__)


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


def _check_empty_quadrants_for_text(
    image_bytes: bytes, quadrant_names: list[str]
) -> dict[str, bool]:
    """Ask the LLM which empty quadrants contain blurred/smeared former text.

    Crops each quadrant and sends it individually for reliable spatial grounding.
    Uses _downscale_for_detection on the crop to handle Converse size limits.
    Parses response with regex (not json.loads) to tolerate malformed output.
    """
    from documentai_api.config.constants import ConfigDefaults
    from documentai_api.utils.bedrock import _downscale_for_detection, _invoke

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

            response = _invoke(
                messages=messages,
                max_tokens=8,
                model_id=ConfigDefaults.BLUR_QUADRANT_MODEL_ID,
                temperature=0.0,
            )
            text = response["output"]["message"]["content"][0]["text"]
            match = _YES_NO_RE.search(text)
            results[name] = match.group(1).upper() == "YES" if match else False
        except Exception as e:
            logger.warning(f"Empty quadrant LLM check failed for {name}: {e}")
            results[name] = False

    return results


def detect_blur(image_bytes: bytes, content_type: str | None = None) -> BlurResult:
    """Detect blur using Textract OCR word confidence scores with quadrant analysis.

    Only runs on images. PDFs and other content types are skipped (returns not blurry).

    Splits the page into 4 quadrants based on word bounding box positions.
    Only quadrants with sufficient words are evaluated. If any populated quadrant
    has too many low-confidence words or low average confidence, the document
    is flagged as blurry.

    Args:
        image_bytes: Image bytes to analyze.
        content_type: MIME type. Non-image types are skipped.

    Returns:
        BlurResult with detection outcomes.
    """
    from documentai_api.config.constants import ConfigDefaults
    from documentai_api.utils.aws_client_factory import AWSClientFactory

    if not content_type:
        content_type = "image/jpeg"

    # Only run on images - PDFs require render-first-page which is out of scope here
    if not content_type.startswith("image/"):
        return BlurResult(is_blurry=False)

    confidence_floor = ConfigDefaults.BLUR_CONFIDENCE_FLOOR
    min_word_count = ConfigDefaults.BLUR_MIN_WORD_COUNT
    max_low_confidence_percent = ConfigDefaults.BLUR_LOW_CONFIDENCE_MAX_PERCENT
    min_avg_confidence = ConfigDefaults.BLUR_QUADRANT_MIN_AVG_CONFIDENCE

    try:
        start = time.time()
        textract = AWSClientFactory.get_textract_client()
        response = textract.detect_document_text(Document={"Bytes": image_bytes})
        elapsed = round(time.time() - start, 2)

        words = [b for b in response["Blocks"] if b["BlockType"] == "WORD"]
        word_count = len(words)

        # No words at all - not a document (blank/dark/non-document image)
        if word_count == 0:
            return BlurResult(
                is_blurry=False,
                is_not_document=True,
                avg_confidence=0.0,
                word_count=0,
                duration_seconds=Decimal(str(elapsed)),
            )

        # Very few words - likely not a document (photo of hand, wall, etc.)
        # rather than a blurry document that lost all its text
        if word_count < min_word_count:
            return BlurResult(
                is_blurry=False,
                is_not_document=True,
                avg_confidence=0.0,
                word_count=word_count,
                duration_seconds=Decimal(str(elapsed)),
            )

        # Partition words into quadrants by bounding box position
        quadrants: dict[str, list[dict[str, Any]]] = {
            "top_left": [],
            "top_right": [],
            "bottom_left": [],
            "bottom_right": [],
        }
        for w in words:
            bbox = w["Geometry"]["BoundingBox"]
            top = bbox["Top"]
            left = bbox["Left"]
            if top < 0.5:
                if left < 0.5:
                    quadrants["top_left"].append(w)
                else:
                    quadrants["top_right"].append(w)
            else:
                if left < 0.5:
                    quadrants["bottom_left"].append(w)
                else:
                    quadrants["bottom_right"].append(w)

        # Only check quadrants that have enough words to evaluate.
        # Empty or sparse quadrants are checked via LLM fallback if they
        # have 0 words - to distinguish blur-destroyed text from non-text regions.
        # Short-circuits after first failure (one blurry quadrant is sufficient).
        failed_quadrants = []
        quadrant_stats = {}
        for name, qwords in quadrants.items():
            if len(qwords) >= min_word_count:
                q_confidences = [w["Confidence"] for w in qwords]
                q_avg = sum(q_confidences) / len(q_confidences)
                q_low = sum(1 for c in q_confidences if c < confidence_floor)
                q_low_pct = (q_low / len(qwords)) * 100
                quadrant_stats[name] = {
                    "word_count": len(qwords),
                    "avg_confidence": round(q_avg, 1),
                    "low_confidence_percent": round(q_low_pct, 1),
                }
                if _check_quadrant(
                    qwords, confidence_floor, max_low_confidence_percent, min_avg_confidence
                ):
                    failed_quadrants.append(name)
                    break
            else:
                quadrant_stats[name] = {
                    "word_count": len(qwords),
                    "avg_confidence": 0.0,
                    "low_confidence_percent": 0.0,
                    "skipped": True,
                }

        # For empty quadrants on text-dense documents, crop each and ask
        # Nova Pro if blur destroyed text in that region (one call per quadrant).
        # Skip if we already found a blurry quadrant via confidence check.
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
                        "llm_detected_text": has_text,
                    }
                    if has_text:
                        failed_quadrants.append(name)

        confidences = [w["Confidence"] for w in words]
        avg_confidence = sum(confidences) / len(confidences)
        low_confidence_words = sum(1 for c in confidences if c < confidence_floor)
        low_confidence_percent = (low_confidence_words / word_count) * 100

        # If any populated quadrant failed, it's blurry (partial/regional blur).
        # If ALL quadrants were sparse (skipped), fall back to whole-page stats
        # so uniformly-blurry pages with scattered words don't escape.
        all_quadrants_skipped = all(q.get("skipped", False) for q in quadrant_stats.values())
        if failed_quadrants:
            is_blurry = True
        elif all_quadrants_skipped:
            is_blurry = (
                avg_confidence < min_avg_confidence
                or low_confidence_percent > max_low_confidence_percent
            )
        else:
            is_blurry = False

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
            duration_seconds=Decimal(str(elapsed)),
        )

    except Exception as e:
        logger.warning(f"Blur detection failed: {e}")
        return BlurResult(is_blurry=False, analysis_failed=True)
