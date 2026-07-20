"""DTOs for document processing pipeline."""

from dataclasses import dataclass
from decimal import Decimal

from documentai_api.config.constants import DocumentCategory


@dataclass
class InternalApiResponse:
    """Shared API response model."""

    validation_passed: bool
    document_category: DocumentCategory | None
    matched_document_class: str | None
    response_code: str
    response_message: str


@dataclass
class FieldMetrics:
    """Field count and confidence metrics for BDA processing."""

    field_count: int
    field_count_not_empty: int
    field_not_empty_avg_confidence: float | None


@dataclass
class ProcessingTimes:
    """Timing data calculated during BDA processing completion."""

    total_processing_time_seconds: Decimal = Decimal(0)
    bda_processing_time_seconds: Decimal = Decimal(0)


@dataclass
class CropResult:
    """Result of the document ROI crop operation."""

    cropped: bool = False
    bounding_box: tuple[float, float, float, float] | None = None
    retained_percentage: Decimal | None = None
    duration_seconds: Decimal | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    model_id: str | None = None


@dataclass
class OptimizationResult:
    """Combined result of single-pass crop + grayscale optimization."""

    crop_result: CropResult
    grayscale_applied: bool = False
    file_size_bytes: int | None = None
    too_large: bool = False
    failed: bool = False


@dataclass
class PageMetadata:
    """Metadata for a multipage document page."""

    page_number: int
    s3_key: str
    s3_bucket_name: str
    original_file_name: str | None = None
    category: str | None = None
    created_at: str | None = None
