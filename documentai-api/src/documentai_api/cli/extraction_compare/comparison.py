import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from documentai_api.constants.processing import ExtractMethod, LlmUsageReason
from documentai_api.models.extraction_compare import CompareFieldResult, CompareResponse
from documentai_api.utils.dates import get_utc_str
from documentai_api.utils.extraction_compare_client import (
    EXPECTED_EMPTY,
    NO_GROUND_TRUTH,
    field_display_values,
    match_icon,
)
from documentai_api.utils.md import to_table

from ._accuracy import (
    _GEO_TOLERANCE,
    _compute_accuracy,
    _fmt_accuracy,
    _fmt_exp_geo,
    _fmt_geo_accuracy,
    _fmt_geometry,
    _geo_match_icon,
)
from ._render import render_template
from ._types import (
    _RUN_STAMP_PREFIX,
    _AccuracyComparison,
    _ComparisonCtx,
    _CostByReason,
    _CostEntry,
    _ResultData,
)


def _method_key(method: str) -> str:
    """Name a method as sidecars and reports do: the OCR-mapping path is recorded as 'llm'."""
    return _ResultData.LLM if method == ExtractMethod.OCR_MAPPING else method


def _build_comparison_ctx(
    filename: str,
    primary_method: str,
    all_fields: list[str],
    primary: dict[str, CompareFieldResult],
    ocr_mapping: dict[str, CompareFieldResult],
    expected: dict[str, str] | None,
    expected_geo: dict[str, list[str]] | None,
    accuracy: dict[str, dict[str, int]],
    run_ts: str,
    durations: dict[str, Any] | None = None,
    cost: dict[str, float] | None = None,
    tokens: dict[str, Any] | None = None,
    cost_by_reason: dict[str, float] | None = None,
    pages: int | None = None,
) -> _ComparisonCtx:
    """Build the Jinja2 context for comparison.md.j2."""
    duration_lines = []
    if durations:
        for raw_method, d in durations.items():
            method = _method_key(raw_method)
            if hasattr(d, "extraction_duration_seconds"):
                extraction = d.extraction_duration_seconds or EXPECTED_EMPTY
                line = f"{method}: {extraction}s extraction"
                if d.bda_invocation_duration_seconds is not None:
                    line += f", {d.bda_invocation_duration_seconds}s BDA invocation"
            else:
                line = f"{method}: {d}s extraction"
            duration_lines.append((method, line))

    cost_by_service = []
    if cost:
        for model_id, entry_cost in cost.items():
            t = (tokens or {}).get(model_id, {})
            cost_by_service.append(
                (
                    model_id,
                    _CostEntry(
                        amount=entry_cost,
                        tokens={
                            "input": t.get("inputTokens", 0),
                            "output": t.get("outputTokens", 0),
                        }
                        if t
                        else None,
                    ),
                )
            )

    acc_ctx = None
    if accuracy:
        acc_ctx = _AccuracyComparison(
            primary=_fmt_accuracy(accuracy.get(_ResultData.PRIMARY)),
            llm=_fmt_accuracy(accuracy.get(_ResultData.LLM)),
            primary_geo=_fmt_geo_accuracy(accuracy.get(_ResultData.PRIMARY_GEO)),
            llm_geo=_fmt_geo_accuracy(accuracy.get(_ResultData.LLM_GEO)),
        )

    table_headers = [
        "Field",
        "Expected",
        f"{primary_method.upper()} Value",
        "OCR / LLM Value",
        f"{primary_method.upper()} Conf",
        "OCR / LLM Conf",
        "Expected Bounding Box",
        f"{primary_method.upper()} Bounding Box",
        "OCR / LLM Bounding Box",
    ]
    table_rows = []
    for field in all_fields:
        p = primary.get(field, CompareFieldResult())
        lm = ocr_mapping.get(field, CompareFieldResult())
        p_val, llm_val, p_conf, llm_conf, exp_val = field_display_values(p, lm, expected, field)
        p_val = p_val.replace("\n", " ")
        llm_val = llm_val.replace("\n", " ")
        primary_geo = _fmt_geometry(p.geometry)
        llm_geo = _fmt_geometry(lm.geometry)
        exp_geo = expected_geo.get(field) if expected_geo else None
        p_geo_cell = (
            f"{_geo_match_icon(exp_geo, primary_geo, tolerance=_GEO_TOLERANCE)} " if exp_geo else ""
        ) + primary_geo
        llm_geo_cell = (
            f"{_geo_match_icon(exp_geo, llm_geo, tolerance=_GEO_TOLERANCE)} " if exp_geo else ""
        ) + llm_geo
        if expected is not None:
            p_icon = (
                match_icon(exp_val, p_val, field_name=field) if exp_val != NO_GROUND_TRUTH else ""
            )
            llm_icon = (
                match_icon(exp_val, llm_val, field_name=field) if exp_val != NO_GROUND_TRUTH else ""
            )
            p_cell = f"{p_icon} {p_val}".strip()
            llm_cell = f"{llm_icon} {llm_val}".strip()
        else:
            p_cell = p_val
            llm_cell = llm_val
        table_rows.append(
            [
                field,
                exp_val,
                p_cell,
                llm_cell,
                p_conf,
                llm_conf,
                _fmt_exp_geo(exp_geo) if exp_geo else EXPECTED_EMPTY,
                p_geo_cell,
                llm_geo_cell,
            ]
        )

    cbr = None
    if cost_by_reason:
        cbr = _CostByReason(
            shared=cost_by_reason.get("shared", 0.0),
            ocr_mapping=cost_by_reason.get(LlmUsageReason.OCR_MAPPING, 0.0),
            primary=cost_by_reason.get("primary", 0.0),
        )

    return _ComparisonCtx(
        filename=filename,
        primary_method=primary_method,
        run_stamp_prefix=_RUN_STAMP_PREFIX,
        run_ts=run_ts,
        durations=duration_lines,
        cost=cost,
        cost_by_service=cost_by_service,
        cost_total=sum(cost.values()) if cost else 0,
        cost_by_reason=cbr,
        pages=pages,
        accuracy=acc_ctx,
        field_table=to_table(table_headers, table_rows),
    )


def write_comparison_md(
    filename: str,
    result: CompareResponse,
    expected: dict[str, str] | None,
    expected_geo: dict[str, list[str]] | None,
    md_dir: Path,
    data_dir: Path,
) -> None:
    """Write per-document field comparison markdown and persist result data sidecar."""
    accuracy = _compute_accuracy(result.primary, result.ocr_mapping, expected, expected_geo)
    completed_at = datetime.now(UTC)
    _write_result_data(filename, result, accuracy, completed_at, data_dir)

    all_fields = sorted(
        set(result.primary)
        | set(result.ocr_mapping)
        | (set(expected) if expected is not None else set())
    )
    ctx = _build_comparison_ctx(
        filename=filename,
        primary_method=result.primary_method,
        all_fields=all_fields,
        primary=result.primary,
        ocr_mapping=result.ocr_mapping,
        expected=expected,
        expected_geo=expected_geo,
        accuracy=accuracy,
        run_ts=get_utc_str(completed_at),
        durations=result.durations,
        cost=result.cost,
        tokens=result.tokens,
        cost_by_reason=result.cost_by_reason,
        pages=result.pages,
    )
    md_dir.mkdir(parents=True, exist_ok=True)
    (md_dir / f"{Path(filename).stem}.md").write_text(render_template("comparison.md.j2", ctx))


def _write_result_data(
    filename: str,
    result: CompareResponse,
    accuracy: dict[str, dict[str, int]],
    completed_at: datetime,
    data_dir: Path,
) -> None:
    result_data = {
        _ResultData.FILENAME: filename,
        _ResultData.COMPLETED_AT: completed_at.isoformat(),
        _ResultData.PRIMARY_METHOD: result.primary_method,
        _ResultData.DURATIONS: {
            _method_key(method): d.extraction_duration_seconds
            for method, d in result.durations.items()
        },
        _ResultData.COST: result.cost,
        _ResultData.COST_BY_REASON: result.cost_by_reason,
        _ResultData.TOKENS: result.tokens,
        _ResultData.PAGES: result.pages,
        _ResultData.ACCURACY: accuracy,
        _ResultData.PRIMARY: {f: r.model_dump() for f, r in result.primary.items()},
        _ResultData.LLM: {f: r.model_dump() for f, r in result.ocr_mapping.items()},
    }
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / f"{Path(filename).stem}.data.json").write_text(
        json.dumps(result_data, default=float)
    )


def regen_comparison_md(results_dir: Path, expected_dir: Path) -> None:
    """Re-render per-document markdown files from existing .data.json sidecars."""
    for sidecar in sorted((results_dir / "data").glob("*.data.json")):
        data = json.loads(sidecar.read_text())
        filename = data[_ResultData.FILENAME]
        primary_method = data.get(_ResultData.PRIMARY_METHOD, ExtractMethod.BDA)
        primary = {
            f: CompareFieldResult.model_validate(v)
            for f, v in data.get(_ResultData.PRIMARY, {}).items()
        }
        ocr_mapping = {
            f: CompareFieldResult.model_validate(v)
            for f, v in data.get(_ResultData.LLM, {}).items()
        }
        expected = _load_expected(filename, expected_dir)
        expected_geo = _load_expected_geometry(filename, expected_dir)
        accuracy = _compute_accuracy(primary, ocr_mapping, expected, expected_geo)
        all_fields = sorted(
            set(primary) | set(ocr_mapping) | (set(expected) if expected else set())
        )
        ctx = _build_comparison_ctx(
            filename=filename,
            primary_method=primary_method,
            all_fields=all_fields,
            primary=primary,
            ocr_mapping=ocr_mapping,
            expected=expected,
            expected_geo=expected_geo,
            accuracy=accuracy,
            run_ts=get_utc_str(_sidecar_completed_at(sidecar, data)),
            durations=data.get(_ResultData.DURATIONS, {}),
            cost=data.get(_ResultData.COST, {}),
            tokens=data.get(_ResultData.TOKENS),
            cost_by_reason=data.get(_ResultData.COST_BY_REASON, {}),
            pages=data.get(_ResultData.PAGES),
        )
        (results_dir / "md" / f"{Path(filename).stem}.md").write_text(
            render_template("comparison.md.j2", ctx)
        )


def _sidecar_completed_at(sidecar: Path, data: dict[str, Any]) -> datetime:
    """When a result was captured: its stored completedAt, else the sidecar's mtime (legacy)."""
    stored = data.get(_ResultData.COMPLETED_AT)
    if stored:
        return datetime.fromisoformat(stored)
    return datetime.fromtimestamp(sidecar.stat().st_mtime, UTC)


def _load_expected(filename: str, expected_dir: Path) -> dict[str, str] | None:
    path = expected_dir / f"{Path(filename).stem}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return {
        k: str(v) if v is not None else EXPECTED_EMPTY for k, v in data.get("fields", {}).items()
    }


def _load_expected_geometry(filename: str, expected_dir: Path) -> dict[str, list[str]] | None:
    path = expected_dir / f"{Path(filename).stem}.json"
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
