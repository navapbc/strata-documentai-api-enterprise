from pathlib import Path

from documentai_api.constants.processing import ExtractMethod

from ._accuracy import _fmt_geo_pct
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


def _row_stat_cards(row: _CostRow) -> tuple[str, str, str, str, str, str, int]:
    """Return (speed_card, speed_color, cost_card, cost_color, accuracy_card, accuracy_color, n)."""
    n = row.doc_count

    primary_accuracy = _parse_rate(row.p_avg["loose"])
    llm_accuracy = _parse_rate(row.l_avg["loose"])
    acc_delta_pts = round((llm_accuracy - primary_accuracy) * 100)
    accuracy_card = f"+{acc_delta_pts} pts" if acc_delta_pts >= 0 else f"{acc_delta_pts} pts"
    accuracy_color = "#16a34a" if acc_delta_pts >= 0 else "#dc2626"

    if row.median_primary and row.median_ocr_mapping:
        if row.median_primary > row.median_ocr_mapping:
            speed_card = f"{row.median_primary / row.median_ocr_mapping:.1f}x faster"
            speed_color = "#16a34a"
        else:
            speed_card = f"{row.median_ocr_mapping / row.median_primary:.1f}x slower"
            speed_color = "#dc2626"
    else:
        speed_card, speed_color = "-", "#1a1a2e"

    if row.ocr_mapping and row.primary:
        if row.primary > row.ocr_mapping:
            cost_card = f"{row.primary / row.ocr_mapping:.1f}x cheaper"
            cost_color = "#16a34a"
        else:
            cost_card = f"{row.ocr_mapping / row.primary:.1f}x pricier"
            cost_color = "#dc2626"
    else:
        cost_card, cost_color = "-", "#1a1a2e"

    return speed_card, speed_color, cost_card, cost_color, accuracy_card, accuracy_color, n


def _build_stats_table(row: _CostRow) -> str:
    """Build an HTML stats table for a cost row."""
    speed_card, speed_color, cost_card, cost_color, _accuracy_card, _accuracy_color, _ = (
        _row_stat_cards(row)
    )
    is_bda = row.method == ExtractMethod.BDA
    primary_label = "BDA" if is_bda else "Textract"
    primary_accuracy = _parse_rate(row.p_avg["loose"])
    llm_accuracy = _parse_rate(row.l_avg["loose"])
    primary_exact = _parse_rate(row.p_avg["exact"])
    llm_exact = _parse_rate(row.l_avg["exact"])
    med_p = f"{row.median_primary:.2f}s" if row.median_primary else "-"
    med_l = f"{row.median_ocr_mapping:.2f}s" if row.median_ocr_mapping else "-"

    def _delta_pts(p: float, llm: float) -> tuple[str, str]:
        d = round((llm - p) * 100)
        return (f"+{d} pts" if d >= 0 else f"{d} pts"), ("#16a34a" if d >= 0 else "#dc2626")

    equiv_delta, equiv_color = _delta_pts(primary_exact, llm_exact)
    loose_delta, loose_color = _delta_pts(primary_accuracy, llm_accuracy)

    p_geo = _fmt_geo_pct(row.p_geo_counts)
    l_geo = _fmt_geo_pct(row.l_geo_counts)
    try:
        geo_delta, geo_color = _delta_pts(
            _parse_rate(p_geo.split(" ")[0]), _parse_rate(l_geo.split(" ")[0])
        )
    except Exception:
        geo_delta, geo_color = "-", "#1a1a2e"

    rows = [
        ("Speed (median)", med_p, med_l, speed_card, speed_color),
        ("Cost", f"${row.primary:.4f}", f"${row.ocr_mapping:.4f}", cost_card, cost_color),
        ("Accuracy (Equiv.)", row.p_avg["exact"], row.l_avg["exact"], equiv_delta, equiv_color),
        (
            "Accuracy (Equiv+Approx.)",
            row.p_avg["loose"],
            row.l_avg["loose"],
            loose_delta,
            loose_color,
        ),
        ("Bounding Box", p_geo, l_geo, geo_delta, geo_color),
    ]
    header = f"<tr><th>Metric</th><th>{primary_label}</th><th>OCR / LLM</th><th>Delta</th></tr>"
    body = "".join(
        f'<tr><td>{m}</td><td>{p}</td><td>{ocr}</td><td style="color:{c}">{d}</td></tr>'
        for m, p, ocr, d, c in rows
    )
    return f"<table>{header}{body}</table>"


def _build_chart_table(cost_rows: list[_CostRow]) -> str:
    """Build the chart image and stats table stacked vertically for the summary markdown."""
    rows = []
    for row in cost_rows:
        is_bda = row.method == ExtractMethod.BDA
        primary_label = "BDA" if is_bda else "Textract"
        slug = "bda_vs_llm" if is_bda else "textract_vs_llm"
        stats = _build_stats_table(row)
        rows.append(
            f"""<tr>
<td style="text-align:center;"><img src="charts/extraction_compare_{slug}_chart.png" alt="{primary_label} vs LLM" style="max-width:400px;"/></td>
</tr>
<tr>
<td>{stats}</td>
</tr>"""
        )
    return '<table style="width:100%">' + "".join(rows) + "</table>\n\n"


def _build_chart_spec(row: _CostRow) -> str:
    """Render a Vega-Lite chart spec from template."""
    is_bda = row.method == ExtractMethod.BDA
    primary_label = "BDA" if is_bda else "Textract"
    _, _, _, _, _, _, n = _row_stat_cards(row)
    primary_accuracy = _parse_rate(row.p_avg["loose"])
    llm_accuracy = _parse_rate(row.l_avg["loose"])
    return render_template(
        "cost_accuracy_chart.vl.json.j2",
        {
            "primary_label": primary_label,
            "n": n,
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
