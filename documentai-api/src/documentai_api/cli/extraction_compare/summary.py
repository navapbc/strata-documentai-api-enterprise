import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from documentai_api.constants.processing import ExtractMethod, LlmUsageReason, TextractOperation
from documentai_api.models.extraction_compare import CompareFieldResult
from documentai_api.utils.dates import get_utc_str
from documentai_api.utils.md import to_table
from documentai_api.utils.numbers import median

from ._accuracy import _avg_accuracy, _compute_accuracy, _fmt_accuracy
from ._render import render_template
from ._types import (
    _NO_ACCURACY,
    _CostRow,
    _CostSection,
    _DocSummaryRow,
    _ResultData,
)
from .charts import _build_chart_table, write_extraction_compare_charts
from .comparison import _load_expected, _load_expected_geometry, _sidecar_completed_at

_RUN_STAMP_PREFIX = "Last run:"
_COST_LABELS = {
    TextractOperation.ANALYZE_DOCUMENT_LAYOUT.value: "textract - AnalyzeDocument (layout)",
}


class _SummaryData(TypedDict):
    rows: list[_DocSummaryRow]
    avg_durations: dict[str, float]
    cost_by_type: dict[str, float]
    reason_totals: dict[str, dict[str, float]]
    primary_dur_by_method: dict[str, list[float]]
    llm_dur_by_method: dict[str, list[float]]
    accuracy_by_method: dict[str, dict[str, list[int]]]


def _aggregate_result_data(
    worker_files: list[Path], results_dir: Path, expected_dir: Path
) -> _SummaryData:
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
    rows: list[_DocSummaryRow] = []

    for md_file in worker_files:
        result_data = results_dir / "data" / md_file.with_suffix(".data.json").name
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

        primary = {
            f: CompareFieldResult.model_validate(v)
            for f, v in data.get(_ResultData.PRIMARY, {}).items()
        }
        ocr_mapping = {
            f: CompareFieldResult.model_validate(v)
            for f, v in data.get(_ResultData.OCR_MAPPING, {}).items()
        }
        expected = _load_expected(filename, expected_dir)
        expected_geo = _load_expected_geometry(filename, expected_dir)
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
            doc_count=len(primary_dur_by_method.get(primary_method_key, [])),
        )
    ]


def _build_doc_summary_table(rows: list[_DocSummaryRow]) -> str:
    """Build the document summary markdown table string."""
    headers = [
        "Document",
        "Primary Method",
        "Total Cost",
        "Primary Cost",
        "OCR/LLM Cost",
        "Cost Delta",
        "Primary Duration",
        "OCR/LLM Duration",
        "Duration Delta",
        "Primary Match Rate (Equiv+Approx.)",
        "OCR/LLM Match Rate (Equiv+Approx.)",
        "Match Rate Delta",
    ]
    table_rows = []
    for filename, primary_method, durations, file_cost, cost_by_reason, acc in rows:
        stem = Path(filename).stem
        link = f"[{stem}](md/{stem}.md)"
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
        p_loose = (
            p_acc.get(_ResultData.EXACT, 0) + p_acc.get(_ResultData.APPROX, 0) if p_acc else None
        )
        p_total = sum(p_acc.values()) if p_acc else None
        l_loose = (
            l_acc.get(_ResultData.EXACT, 0) + l_acc.get(_ResultData.APPROX, 0) if l_acc else None
        )
        l_total = sum(l_acc.values()) if l_acc else None
        if p_loose is not None and p_total and l_loose is not None and l_total:
            delta = (l_loose / l_total) - (p_loose / p_total)
            match_rate_delta = "0%" if delta == 0 else f"{delta:+.1%}"
        else:
            match_rate_delta = "-"
        table_rows.append(
            [
                link,
                primary_method,
                f"${file_cost:.6f}",
                f"${primary_cost:.6f}",
                f"${llm_cost:.6f}",
                f"{cost_delta:+.6f}",
                primary_dur_cell,
                llm_dur_cell,
                dur_delta,
                p_fmt["loose"],
                l_fmt["loose"],
                match_rate_delta,
            ]
        )
    return to_table(headers, table_rows)


def write_extraction_compare_summary(results_dir: Path, expected_dir: Path) -> None:
    """Aggregate per-document .data.json files into a single summary markdown report."""
    worker_files = sorted(
        (f for f in (results_dir / "md").glob("*.md") if f.name != "extraction_compare_summary.md"),
        key=lambda f: f.name,
    )
    if not worker_files:
        return

    result = _aggregate_result_data(worker_files, results_dir, expected_dir)
    completed = [
        _sidecar_completed_at(sidecar, json.loads(sidecar.read_text()))
        for sidecar in (results_dir / "data").glob("*.data.json")
    ]
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

    llm_costs = [
        (_COST_LABELS.get(k, k), v)
        for k, v in sorted(result["cost_by_type"].items())
        if k not in (ExtractMethod.BDA, ExtractMethod.TEXTRACT)
    ]
    ctx = {
        "run_stamp_prefix": _RUN_STAMP_PREFIX,
        "run_ts": get_utc_str(max(completed, default=datetime.now(UTC))),
        "doc_count": len(worker_files),
        "llm_costs": llm_costs,
        "llm_cost_subtotal": sum(v for _, v in llm_costs),
        "cost_sections": [
            _CostSection(
                primary_label="BDA" if row.method == ExtractMethod.BDA else "Textract Identity",
                chart_table=_build_chart_table([row]),
            )
            for row in cost_rows
        ],
        "doc_rows": result["rows"],
        "doc_summary_table": _build_doc_summary_table(result["rows"]) if result["rows"] else "",
    }
    (results_dir / "extraction_compare_summary.md").write_text(
        render_template("summary.md.j2", ctx)
    )
    write_extraction_compare_charts(cost_rows, results_dir)
