"""DTOs for document classification operations."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Self

from documentai_api.dtos.extraction import ExtractionResult


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
    field_missing_geometry_list: list[str] | None = None
    additional_info: str | None = None

    @classmethod
    def from_extraction_result(
        cls, result: ExtractionResult, additional_info: str | None = None
    ) -> Self:
        return cls(
            bda_output_s3_uri=result.output_s3_uri,
            matched_document_class=result.document_type,
            matched_blueprint_name=result.matched_blueprint_name,
            matched_blueprint_confidence=result.matched_blueprint_confidence,
            field_confidence_scores=result.field_confidence_scores,
            field_empty_list=result.field_empty_list,
            field_missing_geometry_list=result.field_missing_geometry_list,
            additional_info=additional_info,
        )


@dataclass
class BedrockClassificationResult:
    document_type: str
    confidence: float
    max_document_count_on_page: int
    max_document_count_on_page_reason: str = ""
    has_multipage_inconsistency: bool = False
    has_multipage_inconsistency_reason: str = ""
    category_match: bool | None = None
    is_identity_document: bool = False
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_seconds: Decimal | None = None
    model_id: str | None = None


@dataclass
class PreclassificationMatchResult:
    """Result of matching a document against known BDA blueprints during preclassification."""

    matched_document_type: str | None = None
    confidence: float = 0.0
    category: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_seconds: Decimal | None = None
