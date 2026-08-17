"""DTOs for DynamoDB write operations."""

from decimal import Decimal
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field

from documentai_api.dtos.classification import (
    BedrockClassificationResult,
    ClassificationData,
    PreclassificationMatchResult,
)
from documentai_api.dtos.processing import InternalApiResponse


def _ddb_metadata_map(attr: str, param: str) -> dict[str, Any]:
    """Helper to attach DDB metadata to a Pydantic Field."""
    return {"ddb_attr": attr, "ddb_param": param}


class PreClassificationDdbFields(BaseModel):
    """Pre-classification metrics shaped for DDB persistence.

    Fields annotated with _ddb_metadata_map are automatically mapped to DynamoDB
    attributes by upsert_ddb. The first arg is the DDB attribute name, the second
    is the expression parameter placeholder.

    Use from_results() to construct from the two classification dataclasses rather
    than setting fields individually.
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
    category_match: bool | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("preclassificationCategoryMatch", ":pccm")
    )
    blueprint_matched_document_type: str | None = Field(
        default=None,
        json_schema_extra=_ddb_metadata_map("preclassificationBlueprintMatchedType", ":pcbmt"),
    )
    blueprint_match_confidence: float | None = Field(
        default=None,
        json_schema_extra=_ddb_metadata_map("preclassificationBlueprintMatchConfidence", ":pcbmc"),
    )
    blueprint_match_input_tokens: int | None = Field(
        default=None,
        json_schema_extra=_ddb_metadata_map(
            "preclassificationBlueprintMatchInputTokens", ":pcbmit"
        ),
    )
    blueprint_match_output_tokens: int | None = Field(
        default=None,
        json_schema_extra=_ddb_metadata_map(
            "preclassificationBlueprintMatchOutputTokens", ":pcbmot"
        ),
    )
    blueprint_match_duration_seconds: Decimal | None = Field(
        default=None,
        json_schema_extra=_ddb_metadata_map(
            "preclassificationBlueprintMatchDurationSeconds", ":pcbmds"
        ),
    )
    max_document_count_on_page: int | None = Field(
        default=None,
        json_schema_extra=_ddb_metadata_map("preclassificationMaxDocumentCountOnPage", ":pcmdcop"),
    )
    max_document_count_on_page_reason: str | None = Field(
        default=None,
        json_schema_extra=_ddb_metadata_map(
            "preclassificationMaxDocumentCountOnPageReason", ":pcmdcopr"
        ),
    )
    has_multipage_inconsistency: bool | None = Field(
        default=None,
        json_schema_extra=_ddb_metadata_map("preclassificationHasMultipageInconsistency", ":pchmi"),
    )
    has_multipage_inconsistency_reason: str | None = Field(
        default=None,
        json_schema_extra=_ddb_metadata_map(
            "preclassificationHasMultipageInconsistencyReason", ":pcpmir"
        ),
    )

    @classmethod
    def from_results(
        cls,
        classification: BedrockClassificationResult,
        blueprint_match: PreclassificationMatchResult | None,
    ) -> Self:
        """Build from the two classification dataclasses."""
        return cls(
            document_type=classification.document_type,
            confidence=classification.confidence,
            category_match=classification.category_match,
            input_tokens=classification.input_tokens,
            output_tokens=classification.output_tokens,
            duration_seconds=classification.duration_seconds,
            model_id=classification.model_id,
            max_document_count_on_page=classification.max_document_count_on_page,
            max_document_count_on_page_reason=classification.max_document_count_on_page_reason,
            has_multipage_inconsistency=classification.has_multipage_inconsistency,
            has_multipage_inconsistency_reason=classification.has_multipage_inconsistency_reason,
            blueprint_matched_document_type=blueprint_match.matched_document_type
            if blueprint_match
            else None,
            blueprint_match_confidence=blueprint_match.confidence if blueprint_match else None,
            blueprint_match_input_tokens=blueprint_match.input_tokens if blueprint_match else None,
            blueprint_match_output_tokens=blueprint_match.output_tokens
            if blueprint_match
            else None,
            blueprint_match_duration_seconds=blueprint_match.duration_seconds
            if blueprint_match
            else None,
        )


class UpdateDdbRecord(BaseModel):
    """Input DTO for update_ddb."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    object_key: str
    status: str
    internal_api_response: InternalApiResponse | None = None
    data: ClassificationData | None = None
    bda_invocation_arn: str | None = None
    bda_project_arn_used: str | None = None
    error_message: str | None = None
    below_extraction_confidence_floor: bool = False
    extraction_rules_configured: bool | None = None
    missing_required_field_list: list[str] | None = None
    required_field_list: list[str] | None = None
    applied_extraction_confidence_floor: float | None = None
    used_default_confidence_floor: bool | None = None
    pages_sent_to_bda: int | None = None
    result_processor_started_at: str | None = None
    bda_invoke_duration_seconds: Decimal | None = None
    bda_invoke_retry_count: int | None = None


class InitialDdbRecord(BaseModel):
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
    system_document_id: str | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("systemDocumentId", ":systemDocumentId")
    )
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
    blur_analysis_failed: bool = False
    ocr_avg_word_confidence: float | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("ocrAvgWordConfidence", ":ocrConf")
    )
    document_word_count: int | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("documentWordCount", ":wordCount")
    )
    blur_llm_checked: bool = False
    blur_reason_text: str | None = Field(
        default=None,
        json_schema_extra=_ddb_metadata_map("isDocumentBlurryReason", ":isDocumentBlurryReason"),
    )
    blur_quadrant_stats: dict[str, Any] | None = Field(
        default=None,
        json_schema_extra=_ddb_metadata_map("documentWordQuadrantStats", ":wordQuadrantStats"),
    )
    pre_classification: PreClassificationDdbFields | None = None
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
    upload_source: str | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("uploadSource", ":uploadSource")
    )
    tenant_id: str | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("tenantId", ":tenantId")
    )
    api_key_name: str | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("apiKeyName", ":clientName")
    )
    is_demo: bool = Field(default=False, json_schema_extra=_ddb_metadata_map("isDemo", ":isDemo"))
    ttl_days: int | None = None  # override default TTL (e.g. 3 for demo uploads)
    document_processor_started_at: str | None = Field(
        default=None,
        json_schema_extra=_ddb_metadata_map("documentProcessorStartedAt", ":dpStartedAt"),
    )
    is_document_processor_cold_start: bool | None = Field(
        default=None,
        json_schema_extra=_ddb_metadata_map("isDocumentProcessorColdStart", ":dpColdStart"),
    )
    processing_percentage: float | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("processingPercentage", ":procPct")
    )
    processing_assigned_value: float | None = Field(
        default=None,
        json_schema_extra=_ddb_metadata_map("processingAssignedValue", ":procAssigned"),
    )
    s3_fetch_duration_seconds: Decimal | None = Field(
        default=None,
        json_schema_extra=_ddb_metadata_map("s3FetchDurationSeconds", ":s3FetchDs"),
    )
    blur_detection_duration_seconds: Decimal | None = Field(
        default=None,
        json_schema_extra=_ddb_metadata_map("blurDetectionDurationSeconds", ":blurDetDs"),
    )
    traceparent: str | None = Field(
        default=None,
        json_schema_extra=_ddb_metadata_map("traceparent", ":traceparent"),
    )
    image_opt_crop_block_duration_seconds: Decimal | None = Field(
        default=None,
        json_schema_extra=_ddb_metadata_map(
            "imageOptCropBlockDurationSeconds", ":imgOptCropBlockDs"
        ),
    )
    image_opt_write_duration_seconds: Decimal | None = Field(
        default=None,
        json_schema_extra=_ddb_metadata_map("imageOptWriteDurationSeconds", ":imgOptWriteDs"),
    )
