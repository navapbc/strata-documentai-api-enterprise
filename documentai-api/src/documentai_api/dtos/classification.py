"""DTOs for document classification operations."""

from dataclasses import dataclass
from decimal import Decimal


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
class BedrockClassificationResult:
    document_type: str
    confidence: float
    document_count: int
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
