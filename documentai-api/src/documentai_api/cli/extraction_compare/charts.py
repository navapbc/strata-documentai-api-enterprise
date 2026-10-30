from pathlib import Path

from documentai_api.constants.processing import ExtractMethod
from documentai_api.utils.extraction_compare_client import EXPECTED_EMPTY

from ._render import render_template
from ._types import _CostRow


def _parse_rate(s: str) -> float:
    """Parse a loose accuracy string like '389/507 (77%)' into a float rate."""
    try:
        num, rest = s.split("/", 1)
        denom = rest.split(" ")[0]
        return int(num) / int(denom)
    except (ValueError, ZeroDivisionError):
        return 0.0


def _delta_pts(p: float, llm: float) -> tuple[str, str]:
    """Return (label, color) for a percentage-point delta between two rates."""
    d = round((llm - p) * 100)
    return (f"+{d} pts" if d >= 0 else f"{d} pts"), ("#16a34a" if d >= 0 else "#dc2626")


def _build_stats_table(row: _CostRow) -> str:
    """Build an HTML stats table for a cost row."""
    is_bda = row.method == ExtractMethod.BDA
    primary_label = "BDA" if is_bda else "Textract"

    if row.median_primary and row.median_ocr_mapping:
        if row.median_primary > row.median_ocr_mapping:
            speed_card, speed_color = (
                f"{row.median_primary / row.median_ocr_mapping:.1f}x faster",
                "#16a34a",
            )
        else:
            speed_card, speed_color = (
                f"{row.median_ocr_mapping / row.median_primary:.1f}x slower",
                "#dc2626",
            )
    else:
        speed_card, speed_color = "-", "#1a1a2e"

    if row.ocr_mapping and row.primary:
        if row.primary > row.ocr_mapping:
            cost_card, cost_color = f"{row.primary / row.ocr_mapping:.1f}x cheaper", "#16a34a"
        else:
            cost_card, cost_color = f"{row.ocr_mapping / row.primary:.1f}x pricier", "#dc2626"
    else:
        cost_card, cost_color = "-", "#1a1a2e"

    primary_accuracy = _parse_rate(row.accuracy.primary["loose"])
    llm_accuracy = _parse_rate(row.accuracy.llm["loose"])
    primary_exact = _parse_rate(row.accuracy.primary["exact"])
    llm_exact = _parse_rate(row.accuracy.llm["exact"])
    med_p = f"{row.median_primary:.2f}s" if row.median_primary else "-"
    med_l = f"{row.median_ocr_mapping:.2f}s" if row.median_ocr_mapping else "-"

    equiv_delta, equiv_color = _delta_pts(primary_exact, llm_exact)
    loose_delta, loose_color = _delta_pts(primary_accuracy, llm_accuracy)

    primary_geo = row.accuracy.primary_geo
    llm_geo = row.accuracy.llm_geo

    if primary_geo is None or llm_geo is None:
        geo_delta, geo_color = "-", "#1a1a2e"
    else:
        geo_delta, geo_color = _delta_pts(
            _parse_rate(primary_geo["exact"]), _parse_rate(llm_geo["exact"])
        )

    return render_template(
        "stats_table.html.j2",
        {
            "primary_label": primary_label,
            "med_p": med_p,
            "med_l": med_l,
            "speed_card": speed_card,
            "speed_color": speed_color,
            "cost_primary": row.primary,
            "cost_ocr": row.ocr_mapping,
            "cost_card": cost_card,
            "cost_color": cost_color,
            "primary_exact": row.accuracy.primary["exact"],
            "llm_exact": row.accuracy.llm["exact"],
            "equiv_delta": equiv_delta,
            "equiv_color": equiv_color,
            "primary_loose": row.accuracy.primary["loose"],
            "llm_loose": row.accuracy.llm["loose"],
            "loose_delta": loose_delta,
            "loose_color": loose_color,
            "primary_geo": primary_geo["exact"] if primary_geo else EXPECTED_EMPTY,
            "llm_geo": llm_geo["exact"] if llm_geo else EXPECTED_EMPTY,
            "geo_delta": geo_delta,
            "geo_color": geo_color,
        },
    )


def _build_chart_table(cost_rows: list[_CostRow]) -> str:
    """Build the chart image and stats table stacked vertically for the summary markdown."""
    return render_template(
        "chart_table.html.j2",
        {
            "rows": [
                (
                    "bda_vs_llm" if row.method == ExtractMethod.BDA else "textract_vs_llm",
                    "BDA" if row.method == ExtractMethod.BDA else "Textract",
                    _build_stats_table(row),
                )
                for row in cost_rows
            ]
        },
    )


def _build_chart_spec(row: _CostRow) -> str:
    """Render a Vega-Lite chart spec from template."""
    is_bda = row.method == ExtractMethod.BDA
    primary_label = "BDA" if is_bda else "Textract"
    primary_accuracy = _parse_rate(row.accuracy.primary["loose"])
    llm_accuracy = _parse_rate(row.accuracy.llm["loose"])
    return render_template(
        "cost_accuracy_chart.vl.json.j2",
        {
            "primary_label": primary_label,
            "n": row.doc_count,
            "bar_data": [
                {"method": primary_label, "cost": round(row.primary, 4)},
                {"method": "OCR/LLM", "cost": round(row.ocr_mapping, 4)},
            ],
            "line_data": [
                {"method": primary_label, "accuracy": round(primary_accuracy * 100, 1)},
                {"method": "OCR/LLM", "accuracy": round(llm_accuracy * 100, 1)},
            ],
            "accuracy_min": max(0, min(primary_accuracy, llm_accuracy) * 100 - 15),
            "accuracy_max": min(100, max(primary_accuracy, llm_accuracy) * 100 + 8),
            "cost_max": round(max(row.primary, row.ocr_mapping) * 1.2, 4),
        },
    )


def write_extraction_compare_charts(cost_rows: list[_CostRow], results_dir: Path) -> None:
    """Write Vega-Lite JSON chart specs for each primary method comparison."""
    charts_dir = results_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    for row in cost_rows:
        slug = "bda_vs_llm" if row.method == ExtractMethod.BDA else "textract_vs_llm"
        (charts_dir / f"extraction_compare_{slug}_chart.vl.json").write_text(_build_chart_spec(row))
