"""Tests for extraction_timing module (engine-agnostic timing and field metrics)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from freezegun import freeze_time

from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.dto import ClassificationData
from documentai_api.utils.extraction_timing import (
    calculate_field_metrics,
    calculate_processing_times,
    calculate_wait_time,
    get_elapsed_time_seconds,
)


def test_get_elapsed_time_seconds():
    """Elapsed time returns Decimal with 2-decimal precision."""
    year = datetime.now().year
    start = datetime(year, 1, 1, 12, 0, 0, tzinfo=UTC)
    end = datetime(year, 1, 1, 12, 0, 5, 500000, tzinfo=UTC)  # 5.5 seconds later

    result = get_elapsed_time_seconds(start, end)

    assert result == Decimal("5.5")
    assert isinstance(result, Decimal)


def test_calculate_processing_times_with_extraction_started_at():
    """Uses extractionStartedAt when present."""
    created_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    extraction_started_at = datetime(2026, 1, 1, 12, 0, 5, tzinfo=UTC)
    completion_time = datetime(2026, 1, 1, 12, 0, 15, tzinfo=UTC)

    ddb_record = {
        DocumentMetadata.CREATED_AT: created_at.isoformat(),
        DocumentMetadata.EXTRACTION_STARTED_AT: extraction_started_at.isoformat(),
    }

    result = calculate_processing_times(ddb_record, completion_time)

    assert result.total_processing_time_seconds == Decimal("15.0")
    assert result.bda_processing_time_seconds == Decimal("10.0")


def test_calculate_processing_times_falls_back_to_bda_started_at():
    """Falls back to bdaStartedAt when extractionStartedAt is absent."""
    created_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    bda_started_at = datetime(2026, 1, 1, 12, 0, 5, tzinfo=UTC)
    completion_time = datetime(2026, 1, 1, 12, 0, 15, tzinfo=UTC)

    ddb_record = {
        DocumentMetadata.CREATED_AT: created_at.isoformat(),
        DocumentMetadata.BDA_STARTED_AT: bda_started_at.isoformat(),
    }

    result = calculate_processing_times(ddb_record, completion_time)

    assert result.total_processing_time_seconds == Decimal("15.0")
    assert result.bda_processing_time_seconds == Decimal("10.0")


def test_calculate_processing_times_no_timestamps():
    """Returns zeros when no timestamps are present."""
    result = calculate_processing_times({}, datetime(2026, 1, 1, 12, 0, 15, tzinfo=UTC))

    assert result.total_processing_time_seconds == Decimal(0)
    assert result.bda_processing_time_seconds == Decimal(0)


@freeze_time("2026-01-01 12:00:10+00:00")
def test_calculate_wait_time():
    """Wait time is delta from createdAt to now."""
    created_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

    ddb_record = {
        DocumentMetadata.CREATED_AT: created_at.isoformat(),
    }

    result = calculate_wait_time(ddb_record)
    assert result == Decimal("10.0")


def test_calculate_wait_time_no_created_at():
    """Returns None when createdAt is absent."""
    result = calculate_wait_time({})
    assert result is None


@pytest.mark.parametrize(
    (
        "field_confidence_scores",
        "field_empty_list",
        "expected_count",
        "expected_non_empty",
        "expected_avg",
    ),
    [
        (None, None, 0, 0, None),
        ([], None, 0, 0, None),
        ([{"field1": 0.95}, {"field2": 0.85}], None, 2, 2, 0.9),
        ([{"field1": 0.95}, {"field2": 0.85}, {"field3": 0.75}], ["field3"], 3, 2, 0.9),
        ([{"field1": 0.8}], ["field1"], 1, 0, None),
    ],
)
def test_calculate_field_metrics(
    field_confidence_scores, field_empty_list, expected_count, expected_non_empty, expected_avg
):
    """Field metrics calculation from classification data."""
    data = ClassificationData(
        field_confidence_scores=field_confidence_scores,
        field_empty_list=field_empty_list,
    )

    metrics = calculate_field_metrics(data)

    assert metrics.field_count == expected_count
    assert metrics.field_count_not_empty == expected_non_empty
    assert metrics.field_not_empty_avg_confidence == pytest.approx(expected_avg)
