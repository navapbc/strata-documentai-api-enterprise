"""Numeric utility functions."""

import re


def clean_number(value: str) -> str:
    """Strip currency symbols, thousands separators, and trailing unit suffixes from a numeric string."""
    value = re.sub(r"[\$,]", "", value).strip()
    match = re.match(r"-?\d+(?:\.\d+)?", value)
    return match.group(0) if match else value


def median(vals: list[float]) -> float | None:
    """Return the median of a list, or None if empty."""
    if not vals:
        return None

    s = sorted(vals)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def normalize(value: float, min_val: float, max_val: float) -> float:
    """Scale a value to 0-1 range using min-max normalization.

    Args:
        value: Value to normalize
        min_val: Minimum value of the range
        max_val: Maximum value of the range

    Returns:
        Normalized value clamped to [0.0, 1.0]
    """
    return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))
