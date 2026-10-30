from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypedDict


class _AccuracyDisplay(TypedDict):
    exact: str
    loose: str
    miss: str


_NO_ACCURACY = _AccuracyDisplay(exact="-", loose="-", miss="-")


class _GeoDisplay(TypedDict):
    exact: str
    miss: str


@dataclass
class _AccuracyComparison:
    primary: _AccuracyDisplay
    llm: _AccuracyDisplay
    primary_geo: _GeoDisplay | None
    llm_geo: _GeoDisplay | None


class _TokenCounts(TypedDict):
    input: int
    output: int


@dataclass
class _CountsPerDoc:
    """Per-document match counts for one kind of extraction, collected across a run."""

    exact: list[int] = field(default_factory=list)
    approx: list[int] = field(default_factory=list)
    miss: list[int] = field(default_factory=list)


@dataclass
class _CostEntry:
    amount: float
    tokens: _TokenCounts | None


@dataclass
class _CostByReason:
    shared: float
    ocr_mapping: float
    primary: float


@dataclass
class _CostSection:
    primary_label: str
    chart_table: str


@dataclass
class _ComparisonCtx:
    filename: str
    primary_method: str
    run_stamp_prefix: str
    run_ts: str
    durations: list[tuple[str, str]]
    cost: dict[str, float] | None
    cost_by_service: list[tuple[str, _CostEntry]]
    cost_total: float
    cost_by_reason: _CostByReason | None
    pages: int | None
    accuracy: _AccuracyComparison | None
    field_table: str


@dataclass
class _CostRow:
    method: str
    shared: float
    primary: float
    ocr_mapping: float
    ratio: str
    median_primary: float | None
    median_ocr_mapping: float | None
    dur_ratio: str
    accuracy: _AccuracyComparison
    doc_count: int


class _ResultData(StrEnum):
    """Result data JSON keys."""

    FILENAME = "filename"
    COMPLETED_AT = "completedAt"
    PRIMARY_METHOD = "primary_method"
    DURATIONS = "durations"
    COST = "cost"
    COST_BY_REASON = "cost_by_reason"
    TOKENS = "tokens"
    PAGES = "pages"
    ACCURACY = "accuracy"
    PRIMARY = "primary"
    LLM = "llm"
    EXACT = "exact"
    APPROX = "approx"
    MISS = "miss"
    PRIMARY_GEO = "primary_geo"
    LLM_GEO = "llm_geo"


_RUN_STAMP_PREFIX = "Last run"


@dataclass
class _DocSummaryRow:
    filename: str
    primary_method: str
    durations: dict[str, float | None]
    cost: float
    cost_by_reason: dict[str, float]
    accuracy: dict[str, dict[str, int]]
