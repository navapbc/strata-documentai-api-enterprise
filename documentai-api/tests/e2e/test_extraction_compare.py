"""E2E tests for /v1/admin/extraction-compare.

Requires a running API (BASE_URL) and AWS credentials with access to the
Cognito user pool and SSM parameter store. The extraction compare admin user and its password
are provisioned by Terraform (infra/environments/dev/main.tf).

Skipped automatically if COGNITO_CLIENT_ID or SSM_PREFIX are not set in the
environment.
"""

import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, TypedDict

import boto3
import pytest

from documentai_api.config.constants import ExtractMethod, LlmUsageReason
from documentai_api.config.env import get_env_config
from documentai_api.models.extraction_compare import CompareFieldResult, CompareResponse
from documentai_api.utils.extraction_compare_client import (
    ICON_APPROX,
    ICON_EXACT,
    ICON_MISS,
    NO_VALUE,
    field_display_values,
    match_icon,
    print_comparison,
    submit_and_poll,
)
from documentai_api.utils.numbers import median

# =============================================================================
# Constants
# =============================================================================

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
_FIXTURES_DIR = Path(__file__).parent.parent / "helpers" / "fixtures" / "test-documents"
TEST_DOCS_DIR = _FIXTURES_DIR / "happy-path"

_EXTRACT_COMPARE_ADMIN_EMAIL = "extract-compare-admin@internal.invalid"
_EXPECTED_DIR = TEST_DOCS_DIR / "expected"
_RESULTS_DIR = Path(__file__).parent / "results" / "extraction_compare"
_GEO_TOLERANCE = 0.025


class _AccuracyDisplay(TypedDict):
    exact: str
    loose: str
    miss: str


_NO_ACCURACY = _AccuracyDisplay(exact="-", loose="-", miss="-")


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


class _ResultData(StrEnum):
    """Result data JSON keys."""

    FILENAME = "filename"
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


# =============================================================================
# Fixtures
# =============================================================================


def _compare_prereqs_missing() -> bool:
    cfg = get_env_config()
    return not (cfg.cognito_client_id and cfg.ssm_prefix)


pytestmark = pytest.mark.skipif(
    _compare_prereqs_missing(),
    reason="COGNITO_CLIENT_ID and SSM_PREFIX must be set",
)


def _load_expected(filename: str) -> dict[str, str] | None:
    path = _EXPECTED_DIR / f"{Path(filename).stem}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return {k: str(v) if v is not None else NO_VALUE for k, v in data.get("fields", {}).items()}


def _load_expected_geometry(filename: str) -> dict[str, list[str]] | None:
    path = _EXPECTED_DIR / f"{Path(filename).stem}.json"
    if not path.exists():
        return None
    raw_geo = json.loads(path.read_text()).get("geometry", {})
    matched = raw_geo.get("matched", {}) if isinstance(raw_geo.get("matched"), dict) else raw_geo

    def _fmt(bb: dict[str, Any]) -> str:
        return f"{bb['left']:.3f},{bb['top']:.3f},{bb['width']:.3f},{bb['height']:.3f}"

    result: dict[str, list[str]] = {}
    for field, entry in matched.items():
        if not isinstance(entry, dict) or "candidates" not in entry:
            continue
        result[field] = [
            _fmt(c) for c in entry["candidates"] if isinstance(c, dict) and "left" in c
        ]
    return result or None


def _compare_files() -> list[str]:
    cases = json.loads((_FIXTURES_DIR / "expected.json").read_text())
    return [
        Path(filename).name
        for filename, entry in cases.items()
        if entry.get("compareEnabled", False)
    ]


_COMPARE_FILES = _compare_files()


# =============================================================================
# Test
# =============================================================================


@pytest.fixture(scope="session")
def compare_jwt(reset_env):
    """Fetch extraction compare admin password from SSM and exchange for a Cognito JWT."""
    os.environ.update(reset_env)
    get_env_config.cache_clear()
    cfg = get_env_config()
    assert cfg.cognito_client_id
    password_param = f"{cfg.ssm_prefix}/extract-compare-admin-password"

    ssm = boto3.client("ssm")
    password = ssm.get_parameter(Name=password_param, WithDecryption=True)["Parameter"]["Value"]

    cognito = boto3.client("cognito-idp")
    response = cognito.initiate_auth(
        ClientId=cfg.cognito_client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": _EXTRACT_COMPARE_ADMIN_EMAIL, "PASSWORD": password},
    )
    return response["AuthenticationResult"]["AccessToken"]


@pytest.mark.parametrize("filename", _COMPARE_FILES)
def test_extraction_compare(filename, compare_jwt):
    """Run extraction compare for a single fixture file and write per-doc results."""
    result = submit_and_poll(BASE_URL, TEST_DOCS_DIR / filename, compare_jwt)

    assert result.job_id
    assert len(result.primary) > 0, "Primary extraction returned no fields"
    assert len(result.ocr_mapping) > 0, "OCR mapping returned no fields"

    print_comparison(filename, result, _load_expected(filename))
    _write_comparison_md(
        filename, result, _load_expected(filename), _load_expected_geometry(filename)
    )


# =============================================================================
# Field comparison helpers
# =============================================================================


def _fmt_geometry(geo: list[dict[str, Any]] | None) -> str:
    if not geo:
        return NO_VALUE

    bb = geo[0].get("boundingBox") or geo[0]
    left, top, w, h = bb.get("left", 0), bb.get("top", 0), bb.get("width", 0), bb.get("height", 0)
    return f"{left:.3f},{top:.3f},{w:.3f},{h:.3f}"


def _geo_match_icon(exp_geo: list[str], actual_geo: str, tolerance: float) -> str:
    """Return best match icon across all valid candidates."""
    icons = [match_icon(candidate, actual_geo, tolerance=tolerance) for candidate in exp_geo]
    for icon in (ICON_EXACT, ICON_APPROX, ICON_MISS):
        if icon in icons:
            return icon
    return ICON_MISS


def _fmt_exp_geo(exp_geo: list[str]) -> str:
    return "|".join(exp_geo)


# =============================================================================
# Accuracy helpers
# =============================================================================


def _compute_accuracy(
    primary: dict[str, CompareFieldResult],
    llm: dict[str, CompareFieldResult],
    expected: dict[str, str] | None,
    expected_geo: dict[str, list[str]] | None = None,
) -> dict[str, dict[str, int]]:
    """Count exact/approx/non-match for primary and llm against expected fields and geometry."""
    if expected is None:
        return {}

    pc: Counter[str] = Counter()
    lc: Counter[str] = Counter()

    for field, ev in expected.items():
        if ev == NO_VALUE:
            continue
        pc[
            match_icon(
                ev,
                str(primary.get(field, CompareFieldResult()).value or NO_VALUE),
                field_name=field,
            )
        ] += 1
        lc[
            match_icon(
                ev, str(llm.get(field, CompareFieldResult()).value or NO_VALUE), field_name=field
            )
        ] += 1

    pgc: Counter[str] = Counter()
    lgc: Counter[str] = Counter()

    if expected_geo:
        for field, exp_geo in expected_geo.items():
            p_geo = _fmt_geometry(primary.get(field, CompareFieldResult()).geometry)
            l_geo = _fmt_geometry(llm.get(field, CompareFieldResult()).geometry)
            # Only score geo when the extractor returned a value; no value means no geometry to evaluate.
            if p_geo != NO_VALUE:
                pgc[_geo_match_icon(exp_geo, p_geo, tolerance=_GEO_TOLERANCE)] += 1
            if l_geo != NO_VALUE:
                lgc[_geo_match_icon(exp_geo, l_geo, tolerance=_GEO_TOLERANCE)] += 1

    result: dict[str, dict[str, int]] = {
        _ResultData.PRIMARY: {
            _ResultData.EXACT: pc[ICON_EXACT],
            _ResultData.APPROX: pc[ICON_APPROX],
            _ResultData.MISS: pc[ICON_MISS],
        },
        _ResultData.OCR_MAPPING: {
            _ResultData.EXACT: lc[ICON_EXACT],
            _ResultData.APPROX: lc[ICON_APPROX],
            _ResultData.MISS: lc[ICON_MISS],
        },
    }
    if expected_geo:
        result[_ResultData.PRIMARY_GEO] = {
            _ResultData.EXACT: pgc[ICON_EXACT],
            _ResultData.APPROX: pgc[ICON_APPROX],
            _ResultData.MISS: pgc[ICON_MISS],
        }
        result[_ResultData.OCR_MAPPING_GEO] = {
            _ResultData.EXACT: lgc[ICON_EXACT],
            _ResultData.APPROX: lgc[ICON_APPROX],
            _ResultData.MISS: lgc[ICON_MISS],
        }
    return result


def _avg_accuracy(exact: list[int], approx: list[int], miss: list[int]) -> _AccuracyDisplay:
    """Return average (exact %, exact+approx %, miss %) across multiple documents."""
    totals_per_doc = [e + ap + m for e, ap, m in zip(exact, approx, miss, strict=False)]
    if not totals_per_doc or sum(totals_per_doc) == 0:
        return _NO_ACCURACY
    avg_exact = sum(e / t for e, t in zip(exact, totals_per_doc, strict=False) if t) / len(
        totals_per_doc
    )
    avg_loose = sum(
        (e + ap) / t for e, ap, t in zip(exact, approx, totals_per_doc, strict=False) if t
    ) / len(totals_per_doc)
    avg_miss = sum(m / t for m, t in zip(miss, totals_per_doc, strict=False) if t) / len(
        totals_per_doc
    )
    return _AccuracyDisplay(
        exact=f"{avg_exact:.0%}", loose=f"{avg_loose:.0%}", miss=f"{avg_miss:.0%}"
    )


def _fmt_accuracy(a: dict[str, int] | None) -> _AccuracyDisplay:
    """Format accuracy counts for a single document as (exact %, exact+approx %, miss %)."""
    if not a:
        return _NO_ACCURACY
    exact, approx, miss = (
        a.get(_ResultData.EXACT, 0),
        a.get(_ResultData.APPROX, 0),
        a.get(_ResultData.MISS, 0),
    )
    total = exact + approx + miss
    if total == 0:
        return _NO_ACCURACY
    return _AccuracyDisplay(
        exact=f"{exact / total:.0%}",
        loose=f"{(exact + approx) / total:.0%}",
        miss=f"{miss / total:.0%}",
    )


def _fmt_geo_accuracy(a: dict[str, int] | None) -> str:
    """Format geo accuracy as 'n/total exact, n miss' raw counts."""
    if not a:
        return "-"
    exact = a.get(_ResultData.EXACT, 0)
    miss = a.get(_ResultData.MISS, 0)
    total = exact + a.get(_ResultData.APPROX, 0) + miss
    if total == 0:
        return "-"
    return f"{exact}/{total} exact, {miss} miss"


# =============================================================================
# Per-document writers
# =============================================================================


def _md_table_header(cols: list[str]) -> tuple[str, str]:
    """Return a markdown table header row and separator row for the given column names."""
    return "| " + " | ".join(cols) + " |", "|---" * len(cols) + "|"


def _write_result_data(
    filename: str, result: CompareResponse, accuracy: dict[str, dict[str, int]]
) -> None:
    """Write per-document result data to a .data.json sidecar file."""
    result_data = {
        _ResultData.FILENAME: filename,
        _ResultData.PRIMARY_METHOD: result.primary_method,
        _ResultData.DURATIONS: {
            method: d.extraction_duration_seconds for method, d in result.durations.items()
        },
        _ResultData.COST: result.cost,
        _ResultData.COST_BY_REASON: result.cost_by_reason,
        _ResultData.ACCURACY: accuracy,
        _ResultData.PRIMARY: {f: r.model_dump() for f, r in result.primary.items()},
        _ResultData.OCR_MAPPING: {f: r.model_dump() for f, r in result.ocr_mapping.items()},
    }
    (_RESULTS_DIR / f"{Path(filename).stem}.data.json").write_text(
        json.dumps(result_data, default=float)
    )


def _write_comparison_md(
    filename: str,
    result: CompareResponse,
    expected: dict[str, str] | None,
    expected_geo: dict[str, list[str]] | None = None,
) -> None:
    """Write per-document field comparison to a markdown file and persist result data."""
    accuracy = _compute_accuracy(result.primary, result.ocr_mapping, expected, expected_geo)
    _write_result_data(filename, result, accuracy)

    primary_method = result.primary_method
    all_fields = sorted(
        set(result.primary)
        | set(result.ocr_mapping)
        | (set(expected) if expected is not None else set())
    )
    results_file = _RESULTS_DIR / f"{Path(filename).stem}.md"
    lines = [f"# {filename}\n", f"\n_Run: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}_\n"]

    if result.durations:
        lines.append("\n## Durations\n")
        for method, d in result.durations.items():
            extraction = d.extraction_duration_seconds or NO_VALUE
            line = f"- {method}: {extraction}s extraction"
            if d.bda_invocation_duration_seconds is not None:
                line += f", {d.bda_invocation_duration_seconds}s BDA invocation"
            lines.append(line)
        lines.append("")

    if result.cost or result.tokens:
        lines.append("\n## Cost\n")
        lines.append("_By Service_")
        for model_id, entry_cost in result.cost.items():
            t = result.tokens.get(model_id, {})
            if t:
                lines.append(
                    f"- {model_id}: ${entry_cost:.8f} ({t.get('inputTokens', 0)} in / {t.get('outputTokens', 0)} out)"
                )
            else:
                lines.append(f"- {model_id}: ${entry_cost:.8f} ({result.pages} page(s))")

        lines.append(f"- **total: ${sum(result.cost.values()):.8f}**")

        if result.cost_by_reason:
            lines.append("")
            lines.append("_By Extraction Method_")
            lines.append(
                f"- shared (preclassification): ${result.cost_by_reason.get('shared', 0.0):.8f}"
            )
            lines.append(
                f"- ocr-mapping extraction: ${result.cost_by_reason.get(LlmUsageReason.OCR_MAPPING, 0.0):.8f}"
            )
            lines.append(
                f"- primary ({primary_method}): ${result.cost_by_reason.get('primary', 0.0):.8f}"
            )
            lines.append(f"- **total: ${sum(result.cost.values()):.8f}**")
        lines.append("")

    if accuracy:
        p_acc = _fmt_accuracy(accuracy.get(_ResultData.PRIMARY))
        l_acc = _fmt_accuracy(accuracy.get(_ResultData.OCR_MAPPING))
        p_geo_acc = _fmt_geo_accuracy(accuracy.get(_ResultData.PRIMARY_GEO))
        l_geo_acc = _fmt_geo_accuracy(accuracy.get(_ResultData.OCR_MAPPING_GEO))
        lines.append("\n## Accuracy")
        lines.append("\n_By Extracted Data_")
        lines.append(
            f"- {primary_method.upper()}: {p_acc['exact']} equivalent, {p_acc['loose']} close, {p_acc['miss']} misses"
        )
        lines.append(
            f"- OCR Mapping: {l_acc['exact']} equivalent, {l_acc['loose']} close, {l_acc['miss']} misses"
        )
        lines.append("\n_By Geometry_")
        lines.append(f"- {primary_method.upper()}: {p_geo_acc}")
        lines.append(f"- OCR Mapping: {l_geo_acc}")
        lines.append("")

    lines.append("\n## Field Comparison")
    header, sep = _md_table_header(
        [
            "Field",
            "Expected",
            f"{primary_method.upper()} Value",
            "LLM (via Textract) Value",
            f"{primary_method.upper()} Conf",
            "LLM Conf",
            "Expected Geo",
            f"{primary_method.upper()} Geometry",
            "LLM Geometry",
        ]
    )
    lines.append(header)
    lines.append(sep)
    for field in all_fields:
        p = result.primary.get(field, CompareFieldResult())
        lm = result.ocr_mapping.get(field, CompareFieldResult())
        p_val, llm_val, p_conf, llm_conf, exp_val = field_display_values(p, lm, expected, field)
        p_val = p_val.replace("\n", " ")
        llm_val = llm_val.replace("\n", " ")
        p_geo = _fmt_geometry(p.geometry)
        llm_geo = _fmt_geometry(lm.geometry)
        exp_geo = expected_geo.get(field) if expected_geo else None
        p_geo_cell = (
            f"{_geo_match_icon(exp_geo, p_geo, tolerance=_GEO_TOLERANCE)} " if exp_geo else ""
        ) + p_geo
        llm_geo_cell = (
            f"{_geo_match_icon(exp_geo, llm_geo, tolerance=_GEO_TOLERANCE)} " if exp_geo else ""
        ) + llm_geo
        if expected is not None:
            p_cell = f"{match_icon(exp_val, p_val, field_name=field)} {p_val}".strip()
            llm_cell = f"{match_icon(exp_val, llm_val, field_name=field)} {llm_val}".strip()
        else:
            p_cell = p_val
            llm_cell = llm_val
        lines.append(
            f"| {field} | {exp_val} | {p_cell} | {llm_cell} | {p_conf} | {llm_conf} | {_fmt_exp_geo(exp_geo) if exp_geo else NO_VALUE} | {p_geo_cell} | {llm_geo_cell} |"
        )
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results_file.write_text("\n".join(lines) + "\n")


# =============================================================================
# Summary report
# =============================================================================


class _SummaryData(TypedDict):
    rows: list[
        tuple[str, str, dict[str, float | None], float, dict[str, float], dict[str, dict[str, int]]]
    ]
    avg_durations: dict[str, float]
    cost_by_type: dict[str, float]
    reason_totals: dict[str, dict[str, float]]
    primary_dur_by_method: dict[str, list[float]]
    llm_dur_by_method: dict[str, list[float]]
    accuracy_by_method: dict[str, dict[str, list[int]]]


def _aggregate_result_data(worker_files: list[Path], results_dir: Path) -> _SummaryData:
    """Read .data.json sidecars and aggregate durations, costs, accuracy, and per-doc rows."""
    duration_sums: dict[str, float] = defaultdict(float)
    duration_counts: dict[str, int] = defaultdict(int)
    primary_dur_by_method: dict[str, list[float]] = defaultdict(list)
    llm_dur_by_method: dict[str, list[float]] = defaultdict(list)
    cost_by_type: dict[str, float] = defaultdict(float)
    reason_totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    accuracy_by_method: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: {
            _ResultData.P_EXACT: [],
            _ResultData.P_APPROX: [],
            _ResultData.P_MISS: [],
            _ResultData.L_EXACT: [],
            _ResultData.L_APPROX: [],
            _ResultData.L_MISS: [],
            _ResultData.P_GEO_EXACT: [],
            _ResultData.P_GEO_APPROX: [],
            _ResultData.P_GEO_MISS: [],
            _ResultData.L_GEO_EXACT: [],
            _ResultData.L_GEO_APPROX: [],
            _ResultData.L_GEO_MISS: [],
        }
    )
    rows = []

    for md_file in worker_files:
        result_data = results_dir / md_file.with_suffix(".data.json").name
        if not result_data.exists():
            continue
        data = json.loads(result_data.read_text())
        filename = data[_ResultData.FILENAME]
        primary_method = data.get(_ResultData.PRIMARY_METHOD, ExtractMethod.BDA)
        file_cost = sum(data[_ResultData.COST].values())

        for cost_key, amount in data[_ResultData.COST].items():
            cost_by_type[cost_key] += amount

        for reason, amount in (data.get(_ResultData.COST_BY_REASON) or {}).items():
            reason_totals[primary_method][reason] += amount

        for method, duration in data[_ResultData.DURATIONS].items():
            if duration is not None:
                duration_sums[method] += duration
                duration_counts[method] += 1

        p_dur = data[_ResultData.DURATIONS].get(primary_method)
        llm_dur = data[_ResultData.DURATIONS].get(ExtractMethod.OCR_MAPPING)

        if p_dur is not None:
            primary_dur_by_method[primary_method].append(p_dur)
        if llm_dur is not None:
            llm_dur_by_method[primary_method].append(llm_dur)

        acc = data.get(_ResultData.ACCURACY) or {}
        primary = {
            f: CompareFieldResult.model_validate(v)
            for f, v in data.get(_ResultData.PRIMARY, {}).items()
        }
        ocr_mapping = {
            f: CompareFieldResult.model_validate(v)
            for f, v in data.get(_ResultData.OCR_MAPPING, {}).items()
        }
        expected = _load_expected(filename)
        expected_geo = _load_expected_geometry(filename)
        acc = _compute_accuracy(primary, ocr_mapping, expected, expected_geo)
        if acc:
            a = accuracy_by_method[primary_method]
            a[_ResultData.P_EXACT].append(
                acc.get(_ResultData.PRIMARY, {}).get(_ResultData.EXACT, 0)
            )
            a[_ResultData.P_APPROX].append(
                acc.get(_ResultData.PRIMARY, {}).get(_ResultData.APPROX, 0)
            )
            a[_ResultData.P_MISS].append(acc.get(_ResultData.PRIMARY, {}).get(_ResultData.MISS, 0))
            a[_ResultData.L_EXACT].append(
                acc.get(_ResultData.OCR_MAPPING, {}).get(_ResultData.EXACT, 0)
            )
            a[_ResultData.L_APPROX].append(
                acc.get(_ResultData.OCR_MAPPING, {}).get(_ResultData.APPROX, 0)
            )
            a[_ResultData.L_MISS].append(
                acc.get(_ResultData.OCR_MAPPING, {}).get(_ResultData.MISS, 0)
            )
            a[_ResultData.P_GEO_EXACT].append(
                acc.get(_ResultData.PRIMARY_GEO, {}).get(_ResultData.EXACT, 0)
            )
            a[_ResultData.P_GEO_APPROX].append(
                acc.get(_ResultData.PRIMARY_GEO, {}).get(_ResultData.APPROX, 0)
            )
            a[_ResultData.P_GEO_MISS].append(
                acc.get(_ResultData.PRIMARY_GEO, {}).get(_ResultData.MISS, 0)
            )
            a[_ResultData.L_GEO_EXACT].append(
                acc.get(_ResultData.OCR_MAPPING_GEO, {}).get(_ResultData.EXACT, 0)
            )
            a[_ResultData.L_GEO_APPROX].append(
                acc.get(_ResultData.OCR_MAPPING_GEO, {}).get(_ResultData.APPROX, 0)
            )
            a[_ResultData.L_GEO_MISS].append(
                acc.get(_ResultData.OCR_MAPPING_GEO, {}).get(_ResultData.MISS, 0)
            )

        rows.append(
            (
                filename,
                data[_ResultData.PRIMARY_METHOD],
                data[_ResultData.DURATIONS],
                file_cost,
                data.get(_ResultData.COST_BY_REASON) or {},
                acc,
            )
        )

    avg_durations = {
        method: duration_sums[method] / duration_counts[method] for method in duration_sums
    }
    return _SummaryData(
        rows=rows,
        avg_durations=avg_durations,
        cost_by_type=cost_by_type,
        reason_totals=reason_totals,
        primary_dur_by_method=primary_dur_by_method,
        llm_dur_by_method=llm_dur_by_method,
        accuracy_by_method=accuracy_by_method,
    )


def _write_doc_summary_table(
    lines: list[str],
    rows: list[
        tuple[str, str, dict[str, float | None], float, dict[str, float], dict[str, dict[str, int]]]
    ],
) -> None:
    """Append the per-document summary table to lines."""
    headers = [
        "Document",
        "Method",
        "Total Cost",
        "Primary Cost",
        "LLM Cost",
        "Cost Delta",
        "Primary Duration",
        "LLM Duration",
        "Duration Delta",
        "Primary Accuracy",
        "LLM Accuracy",
    ]
    lines.append("\n## Document Summary")
    lines.append("\n| " + " | ".join(headers) + " |")
    lines.append("|---" * len(headers) + "|")

    for filename, primary_method, durations, file_cost, cost_by_reason, acc in rows:
        stem = Path(filename).stem
        link = f"[{filename}]({stem}.md)"
        shared_cost = cost_by_reason.get("shared", 0.0)
        primary_cost = cost_by_reason.get("primary", 0.0) + shared_cost
        llm_cost = cost_by_reason.get(LlmUsageReason.OCR_MAPPING, 0.0) + shared_cost
        cost_delta = llm_cost - primary_cost
        primary_dur = durations.get(primary_method)
        llm_dur = durations.get(ExtractMethod.OCR_MAPPING)
        dur_delta = (
            f"{llm_dur - primary_dur:+.2f}s"
            if llm_dur is not None and primary_dur is not None
            else "-"
        )
        primary_dur_cell = f"{primary_dur:.2f}s" if primary_dur is not None else "-"
        llm_dur_cell = f"{llm_dur:.2f}s" if llm_dur is not None else "-"
        p_acc = acc.get(_ResultData.PRIMARY) if acc else None
        l_acc = acc.get(_ResultData.OCR_MAPPING) if acc else None
        p_fmt = _fmt_accuracy(p_acc)
        l_fmt = _fmt_accuracy(l_acc)
        lines.append(
            f"| {link} | {primary_method} | ${file_cost:.6f} | ${primary_cost:.6f} | ${llm_cost:.6f} | {cost_delta:+.6f} | {primary_dur_cell} | {llm_dur_cell} | {dur_delta} | {p_fmt['loose']} | {l_fmt['loose']} |"
        )
    lines.append("")


def _cost_compare_section(
    primary_method_key: str,
    reason_totals: dict[str, dict[str, float]],
    primary_dur_by_method: dict[str, list[float]],
    llm_dur_by_method: dict[str, list[float]],
    accuracy_by_method: dict[str, dict[str, list[int]]],
) -> list[_CostRow]:
    """Return cost/duration/accuracy summary rows for a primary method key, or [] if no data."""
    totals = reason_totals.get(primary_method_key)
    if not totals:
        return []

    shared = totals.get("shared", 0.0)
    primary = totals.get("primary", 0.0)
    llm = totals.get(LlmUsageReason.OCR_MAPPING, 0.0)
    ratio = (
        f"{primary / llm:.1f}x {'cheaper' if llm < primary else 'more expensive'}" if llm else "-"
    )
    median_primary = median(primary_dur_by_method.get(primary_method_key, []))
    median_ocr_mapping = median(llm_dur_by_method.get(primary_method_key, []))
    dur_ratio = (
        f"{median_primary / median_ocr_mapping:.1f}x {'faster' if median_ocr_mapping < median_primary else 'slower'}"
        if median_primary and median_ocr_mapping
        else "-"
    )
    a = accuracy_by_method.get(primary_method_key)

    p_avg = (
        _avg_accuracy(a[_ResultData.P_EXACT], a[_ResultData.P_APPROX], a[_ResultData.P_MISS])
        if a
        else _NO_ACCURACY
    )
    l_avg = (
        _avg_accuracy(a[_ResultData.L_EXACT], a[_ResultData.L_APPROX], a[_ResultData.L_MISS])
        if a
        else _NO_ACCURACY
    )

    def _geo_counts(exact_list: list[int], approx_list: list[int], miss_list: list[int]) -> str:
        exact = sum(exact_list)
        total = exact + sum(approx_list) + sum(miss_list)
        return f"{exact}/{total}" if total else "-"

    p_geo_counts = (
        _geo_counts(
            a[_ResultData.P_GEO_EXACT], a[_ResultData.P_GEO_APPROX], a[_ResultData.P_GEO_MISS]
        )
        if a
        else "-"
    )
    l_geo_counts = (
        _geo_counts(
            a[_ResultData.L_GEO_EXACT], a[_ResultData.L_GEO_APPROX], a[_ResultData.L_GEO_MISS]
        )
        if a
        else "-"
    )

    return [
        _CostRow(
            method=primary_method_key,
            shared=shared,
            primary=primary,
            ocr_mapping=llm,
            ratio=ratio,
            median_primary=median_primary,
            median_ocr_mapping=median_ocr_mapping,
            dur_ratio=dur_ratio,
            p_avg=p_avg,
            l_avg=l_avg,
            p_geo_counts=p_geo_counts,
            l_geo_counts=l_geo_counts,
        )
    ]


def regen_comparison_md(results_dir: Path) -> None:
    """Re-render per-document markdown files from existing .data.json sidecars."""
    for sidecar in sorted(results_dir.glob("*.data.json")):
        data = json.loads(sidecar.read_text())
        filename = data[_ResultData.FILENAME]
        primary_method = data.get(_ResultData.PRIMARY_METHOD, ExtractMethod.BDA)
        primary = {
            f: CompareFieldResult.model_validate(v)
            for f, v in data.get(_ResultData.PRIMARY, {}).items()
        }
        ocr_mapping = {
            f: CompareFieldResult.model_validate(v)
            for f, v in data.get(_ResultData.OCR_MAPPING, {}).items()
        }
        expected = _load_expected(filename)
        expected_geo = _load_expected_geometry(filename)
        accuracy = _compute_accuracy(primary, ocr_mapping, expected, expected_geo)

        all_fields = sorted(
            set(primary) | set(ocr_mapping) | (set(expected) if expected else set())
        )
        results_file = results_dir / f"{Path(filename).stem}.md"
        run_ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        lines = [f"# {filename}\n", f"\n_Run: {run_ts}_\n"]

        durations = data.get(_ResultData.DURATIONS, {})
        if durations:
            lines.append("\n## Durations\n")
            for method, dur in durations.items():
                lines.append(f"- {method}: {dur}s extraction")
            lines.append("")

        cost = data.get(_ResultData.COST, {})
        if cost:
            lines.append("\n## Cost\n")
            lines.append("_By Service_")
            for model_id, entry_cost in cost.items():
                lines.append(f"- {model_id}: ${entry_cost:.8f}")
            lines.append(f"- **total: ${sum(cost.values()):.8f}**")
            cost_by_reason = data.get(_ResultData.COST_BY_REASON, {})
            if cost_by_reason:
                lines.append("")
                lines.append("_By Extraction Method_")
                lines.append(
                    f"- shared (preclassification): ${cost_by_reason.get('shared', 0.0):.8f}"
                )
                lines.append(
                    f"- ocr-mapping extraction: ${cost_by_reason.get(LlmUsageReason.OCR_MAPPING, 0.0):.8f}"
                )
                lines.append(
                    f"- primary ({primary_method}): ${cost_by_reason.get('primary', 0.0):.8f}"
                )
                lines.append(f"- **total: ${sum(cost.values()):.8f}**")
            lines.append("")

        if accuracy:
            p_acc = _fmt_accuracy(accuracy.get(_ResultData.PRIMARY))
            l_acc = _fmt_accuracy(accuracy.get(_ResultData.OCR_MAPPING))
            p_geo_acc = _fmt_geo_accuracy(accuracy.get(_ResultData.PRIMARY_GEO))
            l_geo_acc = _fmt_geo_accuracy(accuracy.get(_ResultData.OCR_MAPPING_GEO))
            lines.append("\n## Accuracy")
            lines.append("\n_By Extracted Data_")
            lines.append(
                f"- {primary_method.upper()}: {p_acc['exact']} equivalent, {p_acc['loose']} close, {p_acc['miss']} misses"
            )
            lines.append(
                f"- OCR Mapping: {l_acc['exact']} equivalent, {l_acc['loose']} close, {l_acc['miss']} misses"
            )
            lines.append("\n_By Geometry_")
            lines.append(f"- {primary_method.upper()}: {p_geo_acc}")
            lines.append(f"- OCR Mapping: {l_geo_acc}")
            lines.append("")

        lines.append("\n## Field Comparison")
        header, sep = _md_table_header(
            [
                "Field",
                "Expected",
                f"{primary_method.upper()} Value",
                "LLM (via Textract) Value",
                f"{primary_method.upper()} Conf",
                "LLM Conf",
                "Expected Geo",
                f"{primary_method.upper()} Geometry",
                "LLM Geometry",
            ]
        )
        lines.append(header)
        lines.append(sep)
        for field in all_fields:
            p = primary.get(field, CompareFieldResult())
            lm = ocr_mapping.get(field, CompareFieldResult())
            p_val, llm_val, p_conf, llm_conf, exp_val = field_display_values(p, lm, expected, field)
            p_val = p_val.replace("\n", " ")
            llm_val = llm_val.replace("\n", " ")
            p_geo = _fmt_geometry(p.geometry)
            llm_geo = _fmt_geometry(lm.geometry)
            exp_geo = expected_geo.get(field) if expected_geo else None
            p_geo_cell = (
                f"{_geo_match_icon(exp_geo, p_geo, tolerance=_GEO_TOLERANCE)} " if exp_geo else ""
            ) + p_geo
            llm_geo_cell = (
                f"{_geo_match_icon(exp_geo, llm_geo, tolerance=_GEO_TOLERANCE)} " if exp_geo else ""
            ) + llm_geo
            if expected is not None:
                p_cell = f"{match_icon(exp_val, p_val, field_name=field)} {p_val}".strip()
                llm_cell = f"{match_icon(exp_val, llm_val, field_name=field)} {llm_val}".strip()
            else:
                p_cell = p_val
                llm_cell = llm_val
            lines.append(
                f"| {field} | {exp_val} | {p_cell} | {llm_cell} | {p_conf} | {llm_conf} | {_fmt_exp_geo(exp_geo) if exp_geo else NO_VALUE} | {p_geo_cell} | {llm_geo_cell} |"
            )
        results_file.write_text("\n".join(lines) + "\n")


def write_extraction_compare_summary(results_dir: Path) -> None:
    """Aggregate per-document .data.json files into a single summary markdown report."""
    worker_files = sorted(
        (f for f in results_dir.glob("*.md") if f.name != "extraction_compare_summary.md"),
        key=lambda f: f.name,
    )
    if not worker_files:
        return

    result = _aggregate_result_data(worker_files, results_dir)
    run_ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines = ["# Extraction Compare Results\n", f"\n_Run: {run_ts}_\n"]

    if result["avg_durations"]:
        lines.append("\n## Avg Durations\n")
        for method, avg in sorted(result["avg_durations"].items()):
            lines.append(f"- {method}: {avg:.2f}s")
        lines.append("")

    if result["cost_by_type"]:
        llm_costs = {
            k: v
            for k, v in result["cost_by_type"].items()
            if k not in (ExtractMethod.BDA, ExtractMethod.TEXTRACT)
        }

        lines.append("\n## Total Cost by Model\n")
        for cost_key, amount in sorted(llm_costs.items()):
            lines.append(f"- {cost_key}: ${amount:.6f}")
        lines.append(f"- **total: ${sum(llm_costs.values()):.6f}**")
        lines.append("")

    cost_rows = _cost_compare_section(
        ExtractMethod.BDA,
        result["reason_totals"],
        result["primary_dur_by_method"],
        result["llm_dur_by_method"],
        result["accuracy_by_method"],
    ) + _cost_compare_section(
        ExtractMethod.TEXTRACT,
        result["reason_totals"],
        result["primary_dur_by_method"],
        result["llm_dur_by_method"],
        result["accuracy_by_method"],
    )

    if cost_rows:
        lines.append("\n## Primary Extraction Method vs. LLM via Textract\n")
        lines.append("### Cost & Duration ")
        header, sep = _md_table_header(
            [
                "Primary Method",
                "Shared (preclass)",
                "Primary Total",
                "LLM Total",
                "LLM vs Primary",
                "Median Primary Duration",
                "Median LLM Duration",
                "LLM vs Primary",
            ]
        )
        lines.append(header)
        lines.append(sep)
        for r in cost_rows:
            med_p_cell = f"{r.median_primary:.2f}s" if r.median_primary is not None else "-"
            med_l_cell = f"{r.median_ocr_mapping:.2f}s" if r.median_ocr_mapping is not None else "-"
            lines.append(
                f"| {r.method} | ${r.shared:.6f} | ${r.primary:.6f} | ${r.ocr_mapping:.6f} | {r.ratio} | {med_p_cell} | {med_l_cell} | {r.dur_ratio} |"
            )
        lines.append("")

        lines.append("\n### Accuracy")
        header, sep = _md_table_header(
            [
                "Primary Method",
                "Equiv Match (Primary / LLM)",
                "Close Match (Primary / LLM)",
                "Geo Match (Primary / LLM)",
            ]
        )
        lines.append(header)
        lines.append(sep)
        lines.extend(
            f"| {r.method} | {r.p_avg['exact']} / {r.l_avg['exact']} | {r.p_avg['loose']} / {r.l_avg['loose']} | {r.p_geo_counts} / {r.l_geo_counts} |"
            for r in cost_rows
        )
        lines.append("")

    if result["rows"]:
        _write_doc_summary_table(lines, result["rows"])

    summary = results_dir / "extraction_compare_summary.md"
    summary.write_text("".join(f"{line}\n" if not line.endswith("\n") else line for line in lines))
