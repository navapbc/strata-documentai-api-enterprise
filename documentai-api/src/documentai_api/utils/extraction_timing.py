"""Extraction timing and field metrics logic (engine-agnostic)."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from documentai_api.logging import get_logger
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.bda import (
    calculate_average_non_empty_confidence,
)
from documentai_api.utils.dto import ClassificationData, FieldMetrics, ProcessingTimes

logger = get_logger(__name__)


def get_elapsed_time_seconds(start_time: datetime, end_time: datetime) -> Decimal:
    """Calculate elapsed time in seconds with 2 decimal precision."""
    return Decimal(str(round((end_time - start_time).total_seconds(), 2)))


def calculate_processing_times(
    ddb_record: dict[str, Any], completion_time: datetime
) -> ProcessingTimes:
    """Calculate extraction processing timing metrics from a DDB record.

    Uses extractionStartedAt with fallback to bdaStartedAt for backwards compat.
    """
    timing_data = ProcessingTimes()

    created_at_str = ddb_record.get(DocumentMetadata.CREATED_AT)
    extraction_started_at_str = ddb_record.get(
        DocumentMetadata.EXTRACTION_STARTED_AT
    ) or ddb_record.get(DocumentMetadata.BDA_STARTED_AT)

    if created_at_str:
        created_at = datetime.fromisoformat(created_at_str)
        total_processing_time_seconds = get_elapsed_time_seconds(created_at, completion_time)
        timing_data.total_processing_time_seconds = total_processing_time_seconds
        logger.info(f"Total processing time: {total_processing_time_seconds:.2f} seconds")

    if extraction_started_at_str:
        extraction_started_at = datetime.fromisoformat(extraction_started_at_str)
        bda_processing_time_seconds = get_elapsed_time_seconds(
            extraction_started_at, completion_time
        )
        timing_data.bda_processing_time_seconds = bda_processing_time_seconds
        logger.info(f"Extraction processing time: {bda_processing_time_seconds:.2f} seconds")

    return timing_data


def calculate_wait_time(ddb_record: dict[str, Any]) -> Decimal | None:
    """Calculate wait time from file creation to extraction start."""
    created_at_str = ddb_record.get(DocumentMetadata.CREATED_AT)

    if not created_at_str:
        return None

    created_at = datetime.fromisoformat(created_at_str)
    return get_elapsed_time_seconds(created_at, datetime.now(UTC))


def calculate_field_metrics(data: ClassificationData) -> FieldMetrics:
    """Calculate field count metrics from classification data."""
    if not data.field_confidence_scores:
        return FieldMetrics(0, 0, None)

    field_count = len(data.field_confidence_scores)
    empty_fields = set(data.field_empty_list or [])

    non_empty_count = sum(
        1
        for field_data in data.field_confidence_scores
        if next(iter(field_data.keys())) not in empty_fields
    )
    avg_confidence = calculate_average_non_empty_confidence(
        data.field_confidence_scores, data.field_empty_list
    )

    return FieldMetrics(field_count, non_empty_count, avg_confidence)
