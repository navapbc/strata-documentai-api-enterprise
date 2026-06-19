"""Data models for document classification and field metrics."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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
class ClassificationData:
    """Data required for document classification operations."""

    bda_output_s3_uri: str | None = None
    matched_document_class: str | None = None
    matched_blueprint_name: str | None = None
    matched_blueprint_confidence: float | None = None
    field_confidence_scores: list[dict[str, float]] | None = None
    field_below_threshold_list: list[str] | None = None
    field_empty_list: list[str] | None = None
    additional_info: str | None = None


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
class BedrockClassificationResult:
    document_type: str
    confidence: float
    document_count: int
    is_document: bool
    is_blurry: bool = False
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_seconds: Decimal | None = None
    model_id: str | None = None


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


def _ddb_metadata_map(attr: str, param: str) -> dict[str, Any]:
    """Helper to attach DDB metadata to a Pydantic Field."""
    return {"ddb_attr": attr, "ddb_param": param}


class PreClassificationData(BaseModel):
    """Pre-classification metrics from Bedrock document analysis.

    Fields annotated with _ddb_metadata_map are automatically mapped to DynamoDB
    attributes by upsert_ddb. The first arg is the DDB attribute name, the second
    is the expression parameter placeholder.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    document_type: str | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("preclassificationCategory", ":pcdt")
    )
    confidence: float | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("preclassificationConfidence", ":pcc")
    )
    input_tokens: int | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("preclassificationInputTokens", ":pcit")
    )
    output_tokens: int | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("preclassificationOutputTokens", ":pcot")
    )
    duration_seconds: Decimal | None = Field(
        default=None,
        json_schema_extra=_ddb_metadata_map("preclassificationDurationSeconds", ":pcds"),
    )
    model_id: str | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("preclassificationModelId", ":pcmi")
    )


class UpsertDdbData(BaseModel):
    """Input DTO for upsert_ddb.

    Fields annotated with _ddb_metadata_map are automatically mapped to DynamoDB
    attributes by upsert_ddb. The first arg is the DDB attribute name, the second
    is the expression parameter placeholder.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    object_key: str
    original_file_name: str
    process_status: str | None = None
    user_provided_document_category: str | None = None
    internal_api_response: InternalApiResponse | None = None
    file_size_bytes: int | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("fileSizeBytes", ":fileSize")
    )
    content_type: str | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("contentType", ":contentType")
    )
    pages_detected: int | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("pagesDetected", ":pages")
    )
    job_id: str | None = Field(default=None, json_schema_extra=_ddb_metadata_map("jobId", ":jobId"))
    trace_id: str | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("traceId", ":traceId")
    )
    batch_id: str | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("batchId", ":batchId")
    )
    # Always written (default False), so handled directly in upsert_ddb rather
    # than via the exclude_unset ddb-metadata path - intentionally no ddb_attr.
    is_password_protected: bool = False
    is_document_blurry: bool = False
    pre_classification: PreClassificationData | None = None
    external_document_id: str | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("externalDocumentId", ":extDocId")
    )
    external_system_id: str | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("externalSystemId", ":extSysId")
    )
    # Always written (default True), so handled directly in upsert_ddb rather
    # than via the exclude_unset ddb-metadata path - intentionally no ddb_attr.
    ai_consent_flag: bool = True
    upload_method: str | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("uploadMethod", ":uploadMethod")
    )
    tenant_id: str | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("tenantId", ":tenantId")
    )
    api_key_name: str | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("apiKeyName", ":clientName")
    )
    is_demo: bool = Field(
        default=False, json_schema_extra=_ddb_metadata_map("isDemo", ":isDemo")
    )
    ttl_days: int | None = None  # override default TTL (e.g. 3 for demo uploads)


@dataclass
class PageMetadata:
    """Metadata for a multipage document page."""

    page_number: int
    s3_key: str
    s3_bucket_name: str
    original_file_name: str | None = None
    category: str | None = None
    created_at: str | None = None
