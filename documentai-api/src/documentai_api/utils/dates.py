"""Date utilities."""

import re
from datetime import UTC, datetime


def get_ttl_epoch_in_days(days: int) -> int:
    """Unix-epoch seconds `days` in the future, for a DynamoDB `ttl` attribute."""
    return int(datetime.now(UTC).timestamp()) + days * 24 * 60 * 60


def validate_yyyymmdd_format(date_str: str) -> datetime:
    """Validate date format is YYYY-MM-DD.

    Args:
        date_str: Date string to validate

    Returns:
        datetime object

    Raises:
        ValueError: If date format is invalid
    """
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD.")

    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError(f"Invalid date format: {date_str}. {e}") from e


def validate_date_range(start_date: str, end_date: str | None = None) -> tuple[str, str]:
    validate_yyyymmdd_format(start_date)
    end_date = end_date or start_date
    validate_yyyymmdd_format(end_date)
    if start_date > end_date:
        raise ValueError("start_date must be before or equal to end_date")
    return start_date, end_date


def strip_time(value: str) -> str:
    """Strip the time component from a datetime string to produce a date-only string.

    '2026-01-08T00:00:00' -> '2026-01-08'
    Non-matching strings are returned unchanged.
    """
    if "T" in value:
        return value.split("T")[0]
    return value


def get_today_iso() -> str:
    """Return today's date as an ISO 8601 string (YYYY-MM-DD), in UTC."""
    return datetime.now(UTC).date().isoformat()


def get_month_prefix(date: str) -> str:
    """Return the year-month portion of an ISO date string (YYYY-MM)."""
    return date[:7]
