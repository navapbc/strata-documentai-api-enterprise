"""Blur detection tests.

Unit tests (no AWS credentials):
    uv run pytest tests/utils/test_blur_detection.py -v -k "not integration"

Integration tests (requires AWS credentials):
    uv run pytest tests/utils/test_blur_detection.py -m integration -v -s
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from documentai_api.utils.blur_detection import (
    _YES_NO_RE,
    _check_quadrant,
    detect_blur,
)

# =============================================================================
# Helpers
# =============================================================================


FIXTURES_DIR = Path(__file__).parent.parent / "helpers" / "fixtures" / "test-documents"
BLURRY_FIXTURES_DIR = FIXTURES_DIR / "blur"

CONTENT_TYPE_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def _get_content_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return CONTENT_TYPE_MAP.get(ext, "application/octet-stream")


class Quadrant:
    TOP_LEFT = (0.1, 0.1)
    TOP_RIGHT = (0.1, 0.6)
    BOTTOM_LEFT = (0.6, 0.1)
    BOTTOM_RIGHT = (0.6, 0.6)


def _quadrant_words(
    count: int, quadrant: tuple[float, float], confidence: float
) -> list[dict[str, object]]:
    """Create `count` synthetic Textract WORD blocks placed in `quadrant`."""
    top, left = quadrant
    word = {
        "BlockType": "WORD",
        "Confidence": confidence,
        "Geometry": {"BoundingBox": {"Top": top, "Left": left, "Width": 0.1, "Height": 0.02}},
        "Text": "word",
    }
    return [word] * count


def _textract_response(words: list[dict[str, object]]) -> dict[str, object]:
    """Wrap word blocks in a Textract detect_document_text response."""
    return {"Blocks": [{"BlockType": "PAGE"}, *words]}


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_textract():
    with patch(
        "documentai_api.services.aws_client_factory.AWSClientFactory.get_textract_client"
    ) as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_llm():
    with patch("documentai_api.utils.blur_detection._check_empty_quadrants_for_text") as mock:
        yield mock


# =============================================================================
# Unit tests - _check_quadrant
# =============================================================================


@pytest.mark.parametrize(
    ("words", "expected"),
    [
        ([{"Confidence": 99.0}] * 10, False),
        ([{"Confidence": 80.0}] * 10, True),
        ([{"Confidence": 99.0}] * 6 + [{"Confidence": 50.0}] * 4, True),
        ([{"Confidence": 95.0}] * 8 + [{"Confidence": 60.0}] * 2, False),
        ([{"Confidence": 85.0}] * 10, False),
        ([{"Confidence": 84.9}] * 10, True),
    ],
)
def test_check_quadrant(words, expected):
    assert _check_quadrant(words, 70.0, 30.0, 85.0) is expected


# =============================================================================
# Unit tests - _YES_NO_RE regex
# =============================================================================


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("YES", "YES"),
        ("NO", "NO"),
        ("```json\nYES\n```", "YES"),
        ("Based on my analysis, the answer is NO.", "NO"),
    ],
)
def test_yes_no_re_matches(text, expected):
    assert _YES_NO_RE.search(text) is not None
    assert _YES_NO_RE.search(text).group(1).upper() == expected  # type: ignore[union-attr]


def test_yes_no_re_no_match():
    assert _YES_NO_RE.search("maybe") is None


# =============================================================================
# Unit tests - detect_blur skips
# =============================================================================


@pytest.mark.parametrize("content_type", ["application/pdf", "text/plain", "application/json"])
def test_detect_blur_non_image_skipped(content_type):
    result = detect_blur(b"fake", content_type)
    assert result.is_blurry is False
    assert result.avg_confidence is None


def test_detect_blur_defaults_to_jpeg_when_no_content_type(mock_textract):
    mock_textract.detect_document_text.return_value = _textract_response([])
    result = detect_blur(b"fake")
    assert result.is_not_document is True


# =============================================================================
# Unit tests - detect_blur not-document
# =============================================================================


@pytest.mark.parametrize("word_count", [0, 3])
def test_detect_blur_not_document(mock_textract, word_count):
    words = _quadrant_words(word_count, Quadrant.TOP_LEFT, 99.0)
    mock_textract.detect_document_text.return_value = _textract_response(words)
    result = detect_blur(b"fake", "image/jpeg")
    assert result.is_blurry is False
    assert result.is_not_document is True
    assert result.word_count == word_count


# =============================================================================
# Unit tests - detect_blur quadrant confidence
# =============================================================================


def test_detect_blur_all_quadrants_sharp(mock_textract, mock_llm):
    words = (
        _quadrant_words(6, Quadrant.TOP_LEFT, 99.0)
        + _quadrant_words(6, Quadrant.TOP_RIGHT, 99.0)
        + _quadrant_words(6, Quadrant.BOTTOM_LEFT, 99.0)
        + _quadrant_words(6, Quadrant.BOTTOM_RIGHT, 99.0)
    )
    mock_textract.detect_document_text.return_value = _textract_response(words)
    result = detect_blur(b"fake", "image/jpeg")
    assert result.is_blurry is False
    assert result.word_count == 24
    assert result.duration_seconds is not None
    assert result.duration_seconds >= 0


def test_detect_blur_quadrant_fails_low_avg(mock_textract, mock_llm):
    words = (
        _quadrant_words(6, Quadrant.TOP_LEFT, 99.0)
        + _quadrant_words(6, Quadrant.TOP_RIGHT, 99.0)
        + _quadrant_words(6, Quadrant.BOTTOM_LEFT, 70.0)
        + _quadrant_words(6, Quadrant.BOTTOM_RIGHT, 99.0)
    )
    mock_textract.detect_document_text.return_value = _textract_response(words)
    result = detect_blur(b"fake", "image/jpeg")
    assert result.is_blurry is True


def test_detect_blur_quadrant_fails_high_low_pct(mock_textract, mock_llm):
    words = (
        _quadrant_words(6, Quadrant.TOP_LEFT, 99.0)
        + _quadrant_words(6, Quadrant.TOP_RIGHT, 99.0)
        + _quadrant_words(3, Quadrant.BOTTOM_RIGHT, 95.0)
        + _quadrant_words(3, Quadrant.BOTTOM_RIGHT, 50.0)
        + _quadrant_words(6, Quadrant.BOTTOM_LEFT, 99.0)
    )
    mock_textract.detect_document_text.return_value = _textract_response(words)
    result = detect_blur(b"fake", "image/jpeg")
    assert result.is_blurry is True


def test_detect_blur_early_exit_skips_remaining_quadrants(mock_textract, mock_llm):
    """First blurry quadrant short-circuits - no LLM call needed."""
    words = (
        _quadrant_words(6, Quadrant.TOP_LEFT, 70.0)  # blurry -> early exit
        + _quadrant_words(6, Quadrant.TOP_RIGHT, 99.0)
        + _quadrant_words(6, Quadrant.BOTTOM_RIGHT, 99.0)
        # bottom_left: 0 words (would trigger LLM if not short-circuited)
    )
    mock_textract.detect_document_text.return_value = _textract_response(words)
    result = detect_blur(b"fake", "image/jpeg")
    assert result.is_blurry is True
    mock_llm.assert_not_called()


# =============================================================================
# Unit tests - detect_blur sparse quadrants / whole-page fallback
# =============================================================================


def test_detect_blur_sparse_quadrant_skipped(mock_textract, mock_llm):
    words = (
        _quadrant_words(6, Quadrant.TOP_LEFT, 99.0)
        + _quadrant_words(6, Quadrant.TOP_RIGHT, 99.0)
        + _quadrant_words(3, Quadrant.BOTTOM_LEFT, 50.0)  # sparse (would fail if evaluated)
        + _quadrant_words(6, Quadrant.BOTTOM_RIGHT, 99.0)
    )
    mock_textract.detect_document_text.return_value = _textract_response(words)
    result = detect_blur(b"fake", "image/jpeg")
    assert result.is_blurry is False
    assert result.quadrant_stats is not None
    assert result.quadrant_stats["bottom_left"]["skipped"] is True


@pytest.mark.parametrize(
    ("confidence", "expected_blurry"),
    [(99.0, False), (70.0, True)],
)
def test_detect_blur_all_quadrants_sparse_fallback(
    mock_textract, mock_llm, confidence, expected_blurry
):
    words = (
        _quadrant_words(2, Quadrant.TOP_LEFT, confidence)
        + _quadrant_words(2, Quadrant.TOP_RIGHT, confidence)
        + _quadrant_words(2, Quadrant.BOTTOM_LEFT, confidence)
        + _quadrant_words(2, Quadrant.BOTTOM_RIGHT, confidence)
    )
    mock_textract.detect_document_text.return_value = _textract_response(words)
    result = detect_blur(b"fake", "image/jpeg")
    assert result.is_blurry is expected_blurry


def test_detect_blur_all_quadrants_sparse_fallback_blurry_high_low_pct(mock_textract, mock_llm):
    # 8 words, 4 below floor = 50% > 30%
    words = (
        _quadrant_words(2, Quadrant.TOP_LEFT, 99.0)
        + _quadrant_words(2, Quadrant.TOP_RIGHT, 99.0)
        + _quadrant_words(2, Quadrant.BOTTOM_LEFT, 50.0)
        + _quadrant_words(2, Quadrant.BOTTOM_RIGHT, 50.0)
    )
    mock_textract.detect_document_text.return_value = _textract_response(words)
    result = detect_blur(b"fake", "image/jpeg")
    assert result.is_blurry is True


# =============================================================================
# Unit tests - detect_blur LLM fallback
# =============================================================================


@pytest.mark.parametrize(
    ("llm_result", "expected_blurry"),
    [({"bottom_left": True}, True), ({"bottom_left": False}, False)],
)
def test_detect_blur_empty_quadrant_llm_fallback(
    mock_textract, mock_llm, llm_result, expected_blurry
):
    words = (
        _quadrant_words(10, Quadrant.TOP_LEFT, 99.0)
        + _quadrant_words(10, Quadrant.TOP_RIGHT, 99.0)
        + _quadrant_words(6, Quadrant.BOTTOM_RIGHT, 99.0)
        # bottom_left: empty -> triggers LLM
    )
    mock_textract.detect_document_text.return_value = _textract_response(words)
    mock_llm.return_value = llm_result

    result = detect_blur(b"fake", "image/jpeg")
    assert result.is_blurry is expected_blurry
    assert result.quadrant_stats is not None
    assert result.quadrant_stats["bottom_left"]["is_text_detected_by_llm"] is expected_blurry
    mock_llm.assert_called_once()


def test_detect_blur_empty_quadrant_no_llm_when_not_dense(mock_textract, mock_llm):
    # 10 words total (< 20), empty quadrants should NOT trigger LLM
    words = _quadrant_words(5, Quadrant.TOP_LEFT, 99.0) + _quadrant_words(
        5, Quadrant.TOP_RIGHT, 99.0
    )
    mock_textract.detect_document_text.return_value = _textract_response(words)

    result = detect_blur(b"fake", "image/jpeg")
    assert result.is_blurry is False
    mock_llm.assert_not_called()
    assert result.quadrant_stats is not None
    assert result.quadrant_stats["bottom_left"]["skipped"] is True


def test_detect_blur_llm_skipped_when_confidence_already_failed(mock_textract, mock_llm):
    words = (
        _quadrant_words(6, Quadrant.TOP_LEFT, 70.0)  # blurry
        + _quadrant_words(10, Quadrant.TOP_RIGHT, 99.0)
        + _quadrant_words(6, Quadrant.BOTTOM_RIGHT, 99.0)
        # bottom_left: empty, but LLM skipped due to early failure
    )
    mock_textract.detect_document_text.return_value = _textract_response(words)

    result = detect_blur(b"fake", "image/jpeg")
    assert result.is_blurry is True
    mock_llm.assert_not_called()


def test_detect_blur_quadrant_fails_low_avg_sets_reason(mock_textract, mock_llm):
    words = (
        _quadrant_words(6, Quadrant.TOP_LEFT, 70.0)
        + _quadrant_words(6, Quadrant.TOP_RIGHT, 99.0)
        + _quadrant_words(6, Quadrant.BOTTOM_LEFT, 99.0)
        + _quadrant_words(6, Quadrant.BOTTOM_RIGHT, 99.0)
    )
    mock_textract.detect_document_text.return_value = _textract_response(words)
    result = detect_blur(b"fake", "image/jpeg")
    assert result.is_blurry is True
    assert result.blur_reason_text is not None
    assert "did not meet" in result.blur_reason_text


def test_detect_blur_llm_fallback_sets_reason(mock_textract, mock_llm):
    words = (
        _quadrant_words(10, Quadrant.TOP_LEFT, 99.0)
        + _quadrant_words(10, Quadrant.TOP_RIGHT, 99.0)
        + _quadrant_words(6, Quadrant.BOTTOM_RIGHT, 99.0)
    )
    mock_textract.detect_document_text.return_value = _textract_response(words)
    mock_llm.return_value = {"bottom_left": True}
    result = detect_blur(b"fake", "image/jpeg")
    assert result.is_blurry is True
    assert result.blur_reason_text is not None
    assert "OCR did not detect" in result.blur_reason_text


def test_detect_blur_page_fallback_sets_reason(mock_textract, mock_llm):
    words = (
        _quadrant_words(2, Quadrant.TOP_LEFT, 70.0)
        + _quadrant_words(2, Quadrant.TOP_RIGHT, 70.0)
        + _quadrant_words(2, Quadrant.BOTTOM_LEFT, 70.0)
        + _quadrant_words(2, Quadrant.BOTTOM_RIGHT, 70.0)
    )
    mock_textract.detect_document_text.return_value = _textract_response(words)
    result = detect_blur(b"fake", "image/jpeg")
    assert result.is_blurry is True
    assert result.blur_reason_text is not None


# =============================================================================
# Unit tests - error handling
# =============================================================================


def test_detect_blur_textract_exception_returns_analysis_failed(mock_textract, mock_llm):
    mock_textract.detect_document_text.side_effect = Exception("Textract down")
    result = detect_blur(b"fake", "image/jpeg")
    assert result.is_blurry is False
    assert result.analysis_failed is True


# =============================================================================
# Integration tests - real AWS calls, requires credentials
#
#     uv run pytest tests/utils/test_blur_detection.py -m integration -v -s
# =============================================================================


_BLURRY_SAMPLES = [
    "synthetic-big-pixels.jpeg",
    "synthetic-disk-defocus.jpeg",
    "synthetic-gen-focus-bg.jpeg",
    "synthetic-ghost-arc.jpeg",
    "synthetic-ghost-linear.jpeg",
    "synthetic-half-blur.jpeg",
    "synthetic-low-light.jpeg",
]

_SHARP_SAMPLES = [
    "synthetic-tax-w2-wage-statement.png",
    "synthetic-public-benefits-income-proof-pay-statement-rendered.png",
    "synthetic-drivers-license-desk-background.jpg",
    "synthetic-public-benefits-income-proof-pay-stub.jpg",
    "synthetic-snap-income-proof-employment-wage-verification-letter-photo.png",
]


@pytest.mark.integration
@pytest.mark.parametrize("filename", _BLURRY_SAMPLES)
def test_blur_detects_blurry(filename, real_aws_credentials):
    """Blurry images should be flagged as is_blurry=True."""
    filepath = BLURRY_FIXTURES_DIR / filename
    if not filepath.exists():
        pytest.skip(f"Fixture not found: {filepath}")

    image_bytes = filepath.read_bytes()
    result = detect_blur(image_bytes, _get_content_type(filename))

    print(
        f"\n{filename}: is_blurry={result.is_blurry}, avg_confidence={result.avg_confidence}, "
        f"word_count={result.word_count}, low_confidence_percent={result.low_confidence_percent}, "
        f"duration={result.duration_seconds}s\n  quadrants={result.quadrant_stats}"
    )

    assert result.is_blurry is True, (
        f"{filename}: expected is_blurry=True, got False\n"
        f"  avg_confidence={result.avg_confidence}, word_count={result.word_count}\n"
        f"  quadrants={result.quadrant_stats}"
    )


@pytest.mark.integration
@pytest.mark.parametrize("filename", _SHARP_SAMPLES)
def test_blur_passes_sharp(filename, real_aws_credentials):
    """Sharp images should NOT be flagged as blurry."""
    filepath = FIXTURES_DIR / filename
    if not filepath.exists():
        pytest.skip(f"Fixture not found: {filepath}")

    image_bytes = filepath.read_bytes()
    result = detect_blur(image_bytes, _get_content_type(filename))

    print(
        f"\n{filename}: is_blurry={result.is_blurry}, avg_confidence={result.avg_confidence}, "
        f"word_count={result.word_count}, low_confidence_percent={result.low_confidence_percent}, "
        f"duration={result.duration_seconds}s\n  quadrants={result.quadrant_stats}"
    )

    assert result.is_blurry is False, (
        f"{filename}: sharp image incorrectly flagged as blurry\n"
        f"  avg_confidence={result.avg_confidence}, word_count={result.word_count}\n"
        f"  quadrants={result.quadrant_stats}"
    )
