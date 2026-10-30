# Testing a private function directly as the formatting logic (+N pts, color) is easier to
# verify here than by asserting on rendered HTML output from _build_stats_table.
from documentai_api.cli.extraction_compare.charts import _delta_pts


def test_delta_pts_positive():
    assert _delta_pts(0.72, 0.75) == ("+3 pts", "#16a34a")


def test_delta_pts_negative():
    assert _delta_pts(0.75, 0.72) == ("-3 pts", "#dc2626")


def test_delta_pts_zero():
    assert _delta_pts(0.75, 0.75) == ("+0 pts", "#16a34a")
