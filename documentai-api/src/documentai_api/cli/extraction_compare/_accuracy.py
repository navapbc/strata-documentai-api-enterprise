from typing import Any

from documentai_api.models.extraction_compare import CompareFieldResult
from documentai_api.utils.extraction_compare_client import (
    EXPECTED_EMPTY,
    ICON_APPROX,
    ICON_EXACT,
    ICON_MISS,
    NO_GROUND_TRUTH,
    match_icon,
)

from ._types import _NO_ACCURACY, _AccuracyDisplay, _ResultData

_GEO_TOLERANCE = 0.025


def _fmt_geometry(geo: list[dict[str, Any]] | None) -> str:
    if not geo:
        return EXPECTED_EMPTY
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
        exact=f"{exact}/{total} ({exact / total:.0%})",
        loose=f"{exact + approx}/{total} ({(exact + approx) / total:.0%})",
        miss=f"{miss}",
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


def _fmt_geo_pct(geo_counts: str) -> str:
    """Append percentage to a 'n/total' geo counts string, e.g. '141/238 (59%)'."""
    if geo_counts == "-" or "/" not in geo_counts:
        return geo_counts
    exact_str, total_str = geo_counts.split("/", 1)
    try:
        exact, total = int(exact_str), int(total_str)
        return f"{exact}/{total} ({exact / total:.0%})" if total else geo_counts
    except ValueError:
        return geo_counts


def _avg_accuracy(exact: list[int], approx: list[int], miss: list[int]) -> _AccuracyDisplay:
    """Return pooled counts and percentage across multiple documents."""
    total_exact = sum(exact)
    total_loose = total_exact + sum(approx)
    total_miss = sum(miss)
    total = total_exact + sum(approx) + total_miss
    if total == 0:
        return _NO_ACCURACY
    return _AccuracyDisplay(
        exact=f"{total_exact}/{total} ({total_exact / total:.0%})",
        loose=f"{total_loose}/{total} ({total_loose / total:.0%})",
        miss=f"{total_miss}",
    )


def _compute_accuracy(
    primary: dict[str, CompareFieldResult],
    llm: dict[str, CompareFieldResult],
    expected: dict[str, str] | None,
    expected_geo: dict[str, list[str]] | None = None,
) -> dict[str, dict[str, int]]:
    """Count exact/approx/non-match for primary and llm against expected fields and geometry."""
    from collections import Counter

    if expected is None:
        return {}

    pc: Counter[str] = Counter()
    lc: Counter[str] = Counter()

    for field, ev in expected.items():
        if ev in (EXPECTED_EMPTY, NO_GROUND_TRUTH):
            continue
        pc[
            match_icon(
                ev,
                str(primary.get(field, CompareFieldResult()).value or EXPECTED_EMPTY),
                field_name=field,
            )
        ] += 1
        lc[
            match_icon(
                ev,
                str(llm.get(field, CompareFieldResult()).value or EXPECTED_EMPTY),
                field_name=field,
            )
        ] += 1

    pgc: Counter[str] = Counter()
    lgc: Counter[str] = Counter()

    if expected_geo:
        for field, exp_geo in expected_geo.items():
            p_geo = _fmt_geometry(primary.get(field, CompareFieldResult()).geometry)
            l_geo = _fmt_geometry(llm.get(field, CompareFieldResult()).geometry)
            pgc[_geo_match_icon(exp_geo, p_geo, tolerance=_GEO_TOLERANCE)] += 1
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
