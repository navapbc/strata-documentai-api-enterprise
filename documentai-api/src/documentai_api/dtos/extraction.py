"""DTO for the common extraction result shape returned by all extraction paths."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass
class ExtractionResult:
    """Common return shape from all extraction paths (BDA, Textract, LLM).

    output_uri points to the extraction output written by the extractor;
    response_builder reads it back via the appropriate ExtractionReader.
    """

    document_type: str
    output_uri: str
    field_confidence_scores: list[dict[str, float]] = field(default_factory=list)
    extract_started_at: datetime | None = None
    extract_completed_at: datetime | None = None
    extract_time: Decimal | None = None
    field_empty_list: list[str] = field(default_factory=list)
    field_missing_geometry_list: list[str] = field(default_factory=list)
    # BDA-only
    matched_blueprint_name: str | None = None
    matched_blueprint_confidence: float | None = None
