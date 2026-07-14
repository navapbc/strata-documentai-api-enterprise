# Blur Detection

Detects blurry document images before they enter the extraction pipeline. A blurry document wastes downstream processing (BDA, Textract AnalyzeID) and produces unreliable results.

## Definition of "Blurry"

**Blurry means "can't be OCR'd reliably"** - not "looks visually imperfect." Documents that Textract reads with high confidence (even with ghosting, fog, or large-text blur) are NOT blurry from a pipeline perspective.

## Architecture

Three-layer detection, each progressively more expensive:


**Layer 1: Textract Confidence (deterministic, cheap)**
  Per-word confidence scores, quadrant-based spatial analysis.
  Catches degraded-but-surviving text.

**Layer 2: Whole-Page Fallback (deterministic, free)**
  When all quadrants are sparse/skipped, checks whole-page stats.
  Catches uniform blur with scattered surviving words.

**Layer 3: Nova Pro Vision (LLM, targeted)**
  Only fires for quadrants with 0 words on text-dense documents.
  Crops the quadrant and asks if it contains blurred former text.
  Catches severe partial blur that completely obliterated text.

## Fail-Open Guarantee

Blur detection never blocks the pipeline on its own failure. If Textract or the LLM throws, `detect_blur` returns `analysis_failed=True` and the document falls through to preclassification. This is intentional - blur detection is best-effort, not a gate.

## Thresholds

All thresholds live in `ConfigDefaults` in `documentai_api/config/constants.py`. See that file for current values. The constants are:

| Constant | Purpose |
|----------|---------|
| `BLUR_CONFIDENCE_FLOOR` | Per-word confidence below this = "low confidence" |
| `BLUR_MIN_WORD_COUNT` | Fewer words than this = `is_not_document` (too sparse to evaluate) |
| `BLUR_LOW_CONFIDENCE_MAX_PERCENT` | Quadrant exceeding this % of low-confidence words = blurry |
| `BLUR_QUADRANT_MIN_AVG_CONFIDENCE` | Per-quadrant avg below this = blurry |
| `BLUR_TEXT_DENSE_MIN_WORDS` | Total word count needed for Layer 3 to fire on empty quadrants |
| `BLUR_QUADRANT_MODEL_ID` | Model used for the Layer 3 vision call (Nova Pro required) |

## LLM Fallback Details (Layer 3)

- **Trigger**: Only when a quadrant has exactly 0 words AND total word count >= `BLUR_TEXT_DENSE_MIN_WORDS`
- **Approach**: Crops the empty quadrant with PIL, sends just the sub-image (no spatial instructions needed)
- **Downscale**: Uses `_downscale_for_detection` on the crop to handle Converse size/format limits (HEIC, TIFF, >3.75MB)
- **Parsing**: Regex (`\b(YES|NO)\b`) - tolerant of markdown fences and malformed output (same lesson as `_parse_bbox`)
- **Fail-safe**: If the LLM call or crop fails, returns False (doesn't block processing)
- **Cost**: ~2-3s latency per empty quadrant, sequential. Text-dense documents usually fill all four quadrants, so Layer 3 rarely fires in practice. When it does fire on a document with 2 empty quadrants, expect 4-6s added latency.

### Why crop instead of full-image + spatial instructions?

Vision models localize named quadrant boundaries poorly. Sending just the cropped sub-image with a plain yes/no question is more reliable, uses fewer input tokens, and eliminates spatial misattribution.

### Why not AWS Nova Lite?

Nova Lite consistently fails to identify severely blurred text as former text, even with an optimized prompt. Pro's visual reasoning is required to infer "this smear was text" from visual evidence.

### Prompt Design

The prompt gives the LLM critical context:
1. "This is from a document with dense text elsewhere" - primes it to expect text
2. "OCR found nothing here" - frames the task as anomaly detection
3. Explicit list of what to look for: blurred, smeared, distorted, faded remnants
4. Explicit exclusion list: blank space, photos, logos, barcodes

### Response Parsing

Uses regex, NOT `json.loads`. Vision models routinely emit markdown fences, preambles, and malformed JSON (documented in `_parse_bbox` docstring). The regex extracts the first YES or NO from whatever the model returns.

## What Each Layer Catches

| Blur Type | Example | Caught By |
|-----------|---------|-----------|
| Uniform degradation | Out-of-focus photo | Layer 1 (quadrant confidence) |
| Partial blur, text survives | Motion blur on half the page | Layer 1 (failed quadrant) |
| Uniform blur, scattered words | Very blurry scan, few words survive | Layer 2 (whole-page fallback) |
| Partial blur, text obliterated (0 words in region) | Half the page is a smear | Layer 3 (LLM vision) |

## Known Limitations

- **Partial blur with 1-4 surviving words**: Layer 3 only fires for quadrants with exactly 0 words. If blur leaves 1-4 low-confidence words in a quadrant, that quadrant is skipped (too sparse to evaluate statistically) but doesn't qualify for the LLM check either. This is the gap between Layer 1 and Layer 3. Acceptable tradeoff - diminishing returns to chase further.
- **LLM non-determinism**: The Nova Pro fallback may occasionally flap on borderline cases at temperature=0. The prompt is optimized to minimize this but it's inherent to LLM-based detection.
- **PDFs**: Not evaluated (would require rendering first page). PDFs skip blur detection entirely.

## Integration with Document Lifecycle

```python
# document_lifecycle.py
blur_result = detect_blur(file_bytes, content_type)

if blur_result.is_not_document:
    # -> ProcessStatus.NO_DOCUMENT_DETECTED
elif blur_result.is_blurry:
    # -> ProcessStatus.BLURRY_DOCUMENT_DETECTED

# Otherwise -> proceed to preclassification
```

## Testing

```bash
# Unit tests (no AWS credentials, ~0.1s)
uv run pytest tests/utils/test_blur_detection.py -k "not integration" -v

# Integration tests (requires AWS credentials)
uv run pytest tests/utils/test_blur_detection.py -m integration -v -s
```

Unit tests cover all branches via mocked Textract/LLM (30 tests). Integration tests run against real AWS with fixture images: 7 blurry in `tests/helpers/fixtures/test-documents/blur/`, 5 sharp in `tests/helpers/fixtures/test-documents/`.
