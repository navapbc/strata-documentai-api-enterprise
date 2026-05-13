import pytest

from documentai_api.utils.dates import validate_date_range, validate_yyyymmdd_format


def test_validate_yyyymmdd_format_valid():
    """Test valid date formats."""
    validate_yyyymmdd_format("2026-02-20")  # should not raise


@pytest.mark.parametrize(
    "invalid_date",
    [
        "2026-2-20",  # missing leading zero
        "2026/02/20",  # incorrect separator
        "20-02-2026",  # incorrect order
        "2026-13-01",  # invalid month
        "2026-02-30",  # invalid day
        "not-a-date",  # invalid
        "",  # empty string
    ],
)
def test_validate_yyyymmdd_format_invalid(invalid_date):
    """Test invalid date formats raise ValueError."""
    with pytest.raises(ValueError, match=r"Invalid date format|does not match|out of range"):
        validate_yyyymmdd_format(invalid_date)


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        ("2026-01-01", "2026-01-31", ("2026-01-01", "2026-01-31")),
        ("2026-01-15", "2026-01-15", ("2026-01-15", "2026-01-15")),
        ("2026-01-15", None, ("2026-01-15", "2026-01-15")),
    ],
)
def test_validate_date_range_valid(start, end, expected):
    assert validate_date_range(start, end) == expected


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ("2026-02-01", "2026-01-01"),  # end before start
        ("bad-date", "2026-01-01"),  # invalid start
        ("2026-01-01", "bad-date"),  # invalid end
    ],
)
def test_validate_date_range_invalid(start, end):
    with pytest.raises(
        ValueError, match=r"Invalid date format|start_date must be before or equal to end_date"
    ):
        validate_date_range(start, end)
