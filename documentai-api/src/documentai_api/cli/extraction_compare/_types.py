from dataclasses import dataclass
from enum import StrEnum
from typing import TypedDict


class _AccuracyDisplay(TypedDict):
    exact: str
    loose: str
    miss: str


_NO_ACCURACY = _AccuracyDisplay(exact="-", loose="-", miss="-")


@dataclass
class _AccuracyCtx:
    p: _AccuracyDisplay
    ocr: _AccuracyDisplay
    p_geo: str
    ocr_geo: str


@dataclass
class _CostEntry:
    amount: float
    tokens: dict[str, int] | None  # {"input": int, "output": int}


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
    accuracy: _AccuracyCtx | None
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
    p_avg: _AccuracyDisplay
    l_avg: _AccuracyDisplay
    p_geo_counts: str
    l_geo_counts: str
    doc_count: int


class _ResultData(StrEnum):
    """Result data JSON keys."""

    FILENAME = "filename"
    COMPLETED_AT = "completedAt"
    PRIMARY_METHOD = "primary_method"
    DURATIONS = "durations"
    COST = "cost"
    COST_BY_REASON = "cost_by_reason"
    ACCURACY = "accuracy"
    PRIMARY = "primary"
    OCR_MAPPING = "ocr-mapping"
    EXACT = "exact"
    APPROX = "approx"
    MISS = "miss"
    P_EXACT = "p_exact"
    P_APPROX = "p_approx"
    P_MISS = "p_miss"
    L_EXACT = "l_exact"
    L_APPROX = "l_approx"
    L_MISS = "l_miss"
    PRIMARY_GEO = "primary_geo"
    OCR_MAPPING_GEO = "ocr-mapping_geo"
    P_GEO_EXACT = "p_geo_exact"
    P_GEO_APPROX = "p_geo_approx"
    P_GEO_MISS = "p_geo_miss"
    L_GEO_EXACT = "l_geo_exact"
    L_GEO_APPROX = "l_geo_approx"
    L_GEO_MISS = "l_geo_miss"


_DocSummaryRow = tuple[
    str, str, dict[str, float | None], float, dict[str, float], dict[str, dict[str, int]]
]
