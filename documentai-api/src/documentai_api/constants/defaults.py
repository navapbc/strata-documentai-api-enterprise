import re


class SystemDefaults:
    # === Batch / upload limits ===
    MAX_BATCH_SIZE = 25
    MAX_PAGES_PER_BUILD = 50
    MAX_SEARCH_JOB_IDS = 25
    MAX_UPLOAD_SIZE_BYTES = 500 * 1024 * 1024  # 500MB

    # === ZIP extraction limits ===
    MAX_ZIP_DECOMPRESSION_RATIO = 100
    MAX_ZIP_EXTRACTED_BYTES = 500 * 1024 * 1024  # 500MB

    # === Misc ===
    DEFAULT_DDB_ERROR_MESSAGE = "Internal processing error"
    UUID_PATTERN = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

    FIELD_CONFIDENCE_THRESHOLD = 0.65
    POLL_INTERVAL_SECONDS = 5
    BDA_REGION_NOT_AVAILABLE = "N/A"
    LOG_RETENTION_DAYS = 30
    DOCUMENT_BATCHES_TTL_DAYS = 30
    DOCUMENT_BUILDS_TTL_DAYS = 30
    DOCUMENT_METADATA_TTL_DAYS = 180
    DEMO_DOCUMENT_TTL_DAYS = 7
    TEST_RUN_DOCUMENT_TTL_DAYS = 7
    PROCESSING_REAPER_STALE_THRESHOLD_HOURS = 1
    TENANT_REQUEST_COUNTS_TTL_DAYS = 365 * 5
    BDA_DOCUMENT_DETECTION_MIN_CHAR_LENGTH = 50
    BLURRY_DOCUMENT_THRESHOLD = 25

    # Textract-based blur detection thresholds
    BLUR_CONFIDENCE_FLOOR = 70.0  # per-word confidence % below which a word is "low confidence"
    BLUR_MIN_WORD_COUNT = 5  # fewer words than this -> is_not_document (too sparse to evaluate)
    BLUR_LOW_CONFIDENCE_MAX_PERCENT = (
        30.0  # if >30% of words in a quadrant are below floor -> blurry
    )
    BLUR_QUADRANT_MIN_AVG_CONFIDENCE = 85.0  # per-quadrant avg confidence below this -> blurry
    BLUR_TEXT_DENSE_MIN_WORDS = (
        20  # total words needed to consider empty quadrants suspicious (LLM fallback gate)
    )
    BLUR_QUADRANT_MODEL_ID = "us.amazon.nova-pro-v1:0"  # model for empty-quadrant blur check (Pro needed for spatial reasoning)
    MISSING_GEOMETRY_CONFIDENCE_THRESHOLD = 0.25
    BDA_MAX_IMAGE_SIZE_BYTES = 5_242_880

    # PIL pixel limit for DecompressionBomb protection. 60 MP covers high-res phone
    # photos of ID documents (typical range 8-48 MP) while still bounding memory use.
    MAX_IMAGE_PIXELS = 60_000_000

    BDA_MAX_DOCUMENT_FILE_SIZE_BYTES = 524_288_000
    # Bedrock Converse per-image limits (used by the vision bbox-detection call).
    # The real API ceiling is 3.75MB / 8000px per image - stricter than the 5MB BDA
    # limit above - so oversized images are downscaled in-memory just for detection.
    BEDROCK_CONVERSE_MAX_IMAGE_BYTES = 3_750_000
    BEDROCK_CONVERSE_MAX_IMAGE_DIMENSION_PX = 8000
    DDB_EMIT_CUSTOM_CLOUDWATCH_METRICS = False
    MAX_PAGES_PER_DOCUMENT = 5
    PRESIGNED_URL_SIGNATURE_VERSION = "s3v4"
    PRESIGNED_PREVIEW_EXPIRY_SECONDS = 300
    PROCESSING_PERCENTAGE_CACHE_TTL_MINUTES = 5


class PreClassificationDefaults:
    MODEL_ID = "us.amazon.nova-pro-v1:0"
    # Converse API supports more document types (csv, html, txt, md, docx, xlsx)
    # but those are rejected at the upload layer before reaching preclassification.
    SUPPORTED_CONTENT_TYPES = (
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "application/pdf",
    )
    PROMPT = "\n".join(
        [
            'Analyze the provided document against the target category: "{user_category}".',
            "",
            "First, perform this evaluation step-by-step:",
            "1. Examine the visual layout of the page. Look for distinct borders, separate rectangles, multiple photos, or independent snippets (e.g., multiple receipts or cards placed on a single scanner bed).",
            "2. For each page, count how many individual, separate documents or items are visually present. max_document_count_on_page is the highest per-page count across the document, not a sum across pages.",
            "3. Evaluate multi-page consistency: pages belong together only if they are clearly continuation pages of the exact same document instance for the exact same individual (e.g. page 2 of the same W2, the same bank statement continued).",
            '4. Check if the document is directly and primarily a "{user_category}" document.',
            '   - Set category_match to false if: the document type does not match "{user_category}", max_document_count_on_page > 1, or has_multipage_inconsistency is true.',
            "",
            "Then, output your final answer strictly as a raw JSON object with no markdown formatting or backticks:",
            "{",
            '  "document_type": "<short description>",',
            '  "confidence": <float between 0.0 and 1.0>,',
            '  "max_document_count_on_page": <integer, maximum number of distinct visual document items found on any single page>,',
            '  "max_document_count_on_page_reason": "<brief explanation of what was counted on each page>",',
            '  "has_multipage_inconsistency": <false only if all pages are continuations of the exact same document instance for the exact same individual, otherwise true>,',
            '  "has_multipage_inconsistency_reason": "<brief explanation of why pages are consistent or inconsistent>",',
            '  "category_match": <true or false based on step 4>,',
            '  "is_identity_document": <true if passport or driver\'s license, else false>',
            "}",
        ]
    )


class PreprocessingBoundingBoxDefaults:
    """Defaults for document bounding-box detection used to crop images before BDA."""

    # Vision model used for ROI detection. Kept separate from the preclassification
    # model so the two can be tuned/swapped independently (they happen to share a
    # default today, but bbox detection and classification are different tasks).
    MODEL_ID = "us.amazon.nova-lite-v1:0"

    PROMPT = "\n".join(
        [
            "Locate the single primary document, ID card, or form in this image.",
            "Return ONLY its bounding box as JSON, no other text:",
            '{"bounding_box": [x1, y1, x2, y2]}',
            "Coordinates use a 0-1000 scale (x1,y1 = top-left, x2,y2 = bottom-right).",
            "Draw the box tightly around the document, excluding background, hands, and surfaces.",
            'If no document is clearly present, respond {"bounding_box": null}.',
        ]
    )

    # tolerant of the malformed JSON vision models routinely emit (stray brackets,
    # missing braces): pulls the four bounding_box numbers rather than json.loads.
    ARRAY_RE = re.compile(
        r"bounding_box\"?\s*:\s*\[\s*"
        r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*,\s*"
        r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)"
    )
