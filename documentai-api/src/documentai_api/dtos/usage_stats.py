"""Usage metrics DTO - S3 contract between usage_report job and API."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass, fields
from typing import Any


@dataclass
class UsageStats:
    """The six usage metric fields shared across job writes and API reads.

    All fields default to 0 for backward compatibility - an old stats.json
    missing a newly added field reads as 0, not an error.
    """

    total_records: int = 0
    total_bda_invocations: int = 0
    total_file_size_bytes: int = 0
    total_bda_pages: int = 0
    total_bedrock_input_tokens: int = 0
    total_bedrock_output_tokens: int = 0

    @classmethod
    def sum(cls, items: Iterable[UsageStats]) -> UsageStats:
        """Sum multiple UsageStats into one."""
        total = cls()
        for item in items:
            total = UsageStats(
                **{f.name: getattr(total, f.name) + getattr(item, f.name) for f in fields(total)}
            )
        return total

    def to_dict(self) -> dict[str, int]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UsageStats:
        """Construct from a flat dict, defaulting missing or null fields to 0."""
        # 'or 0' handles both missing keys and explicit None (e.g. partial S3 writes)
        # using 'or 0' rather than int(data.get(f.name, 0)) to avoid TypeError on None
        return cls(**{f.name: int(data.get(f.name) or 0) for f in fields(cls)})

    @classmethod
    def from_aggregator(cls, daily_stat: dict[str, Any]) -> UsageStats:
        """Construct from the metrics aggregator's nested format."""
        usage = daily_stat.get("usage_stats", {})
        return cls(
            total_records=int(daily_stat.get("total_records") or 0),
            total_bda_invocations=int(daily_stat.get("total_bda_invocations") or 0),
            total_file_size_bytes=int(usage.get("total_file_size_bytes") or 0),
            total_bda_pages=int(usage.get("total_bda_pages") or 0),
            total_bedrock_input_tokens=int(usage.get("total_bedrock_input_tokens") or 0),
            total_bedrock_output_tokens=int(usage.get("total_bedrock_output_tokens") or 0),
        )
