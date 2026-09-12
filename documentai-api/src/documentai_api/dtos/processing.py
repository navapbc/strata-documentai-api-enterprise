"""DTOs for document processing pipeline."""

from concurrent.futures import Future
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Self

from documentai_api.config.constants import ProcessStatus
from documentai_api.dtos.classification import ClassificationData
from documentai_api.dtos.extraction import ExtractionResult


@dataclass
class ReaderResult:
    """Normalized return shape from all extraction readers."""

    field_confidence_map_list: list[dict[str, float]]
    field_values: dict[str, Any]
    field_geometry: dict[str, Any]
    empty_fields: list[str] = field(default_factory=list)
    fields_missing_geometry: list[str] = field(default_factory=list)
    confidence_scores: list[float] = field(default_factory=list)

    @classmethod
    def empty(cls) -> Self:
        return cls(field_confidence_map_list=[], field_values={}, field_geometry={})


@dataclass
class ProcessorResult:
    """Return shape from processors - carries everything pipeline needs to classify."""

    object_key: str
    tenant_id: str | None = None
    batch_id: str | None = None
    result_processor_started_at: str | None = None
    # success path
    extraction_result: ExtractionResult | None = None
    output_uri: str | None = None
    # non-success paths
    classification_data: ClassificationData | None = None
    status: ProcessStatus | None = None


@dataclass
class InternalApiResponse:
    """Shared API response model."""

    validation_passed: bool
    document_category: str | None
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
    crop_block_duration_seconds: Decimal | None = None
    write_duration_seconds: Decimal | None = None


@dataclass
class PageMetadata:
    """Metadata for a multipage document page."""

    page_number: int
    s3_key: str
    s3_bucket_name: str
    original_file_name: str | None = None
    category: str | None = None
    created_at: str | None = None


@dataclass
class PreExtractionResult:
    """Carries pre-extraction outputs from upsert_initial_ddb_record to the doc-processor job."""

    bbox_future: Future[Any] | None
    is_identity_document: bool = False
