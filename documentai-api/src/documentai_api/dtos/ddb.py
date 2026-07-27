"""DTOs for DynamoDB write operations."""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from documentai_api.dtos.processing import InternalApiResponse


def _ddb_metadata_map(attr: str, param: str) -> dict[str, Any]:
    """Helper to attach DDB metadata to a Pydantic Field."""
    return {"ddb_attr": attr, "ddb_param": param}


class PreClassificationDdbFields(BaseModel):
    """Pre-classification metrics shaped for DDB persistence.

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
    blur_analysis_failed: bool = False
    ocr_avg_word_confidence: float | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("ocrAvgWordConfidence", ":ocrConf")
    )
    document_word_count: int | None = Field(
        default=None, json_schema_extra=_ddb_metadata_map("documentWordCount", ":wordCount")
    )
    blur_llm_checked: bool = False
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
