"""Tests for how extraction-compare results record and render their run time."""

import json
import os
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from tests.e2e import test_extraction_compare as compare_results


def test_format_run_stamp_renders_utc_to_the_minute() -> None:
    completed = datetime(2026, 10, 28, 15, 13, 22, 123456, tzinfo=UTC)

    assert compare_results._format_run_stamp(completed) == "2026-10-28 15:13 UTC"


def test_format_run_stamp_converts_other_timezones_to_utc() -> None:
    completed = datetime(2026, 10, 28, 11, 13, tzinfo=timezone(timedelta(hours=-4)))

    assert compare_results._format_run_stamp(completed) == "2026-10-28 15:13 UTC"


def test_completed_at_prefers_the_stored_value(tmp_path: Path) -> None:
    sidecar = tmp_path / "doc.data.json"
    sidecar.write_text("{}")
    stored = "2026-10-28T15:13:22+00:00"

    result = compare_results._sidecar_completed_at(
        sidecar, {compare_results._ResultData.COMPLETED_AT: stored}
    )

    assert result == datetime(2026, 10, 28, 15, 13, 22, tzinfo=UTC)


def test_completed_at_falls_back_to_the_sidecar_mtime_for_legacy_files(tmp_path: Path) -> None:
    sidecar = tmp_path / "doc.data.json"
    sidecar.write_text(json.dumps({"filename": "doc.pdf"}))
    mtime = datetime(2026, 10, 1, 2, 38, tzinfo=UTC)
    os.utime(sidecar, (mtime.timestamp(), mtime.timestamp()))

    assert compare_results._sidecar_completed_at(sidecar, {"filename": "doc.pdf"}) == mtime


def test_clear_results_removes_only_that_documents_results(tmp_path: Path) -> None:
    (tmp_path / "md").mkdir()
    (tmp_path / "data").mkdir()
    for name in ("a.md", "b.md"):
        (tmp_path / "md" / name).write_text("from an earlier run")
    for name in ("a.data.json", "b.data.json"):
        (tmp_path / "data" / name).write_text("from an earlier run")

    compare_results._clear_results("a.pdf", results_dir=tmp_path)

    assert {p.name for p in (tmp_path / "md").iterdir()} == {"b.md"}
    assert {p.name for p in (tmp_path / "data").iterdir()} == {"b.data.json"}


def test_clear_results_creates_the_result_dirs_and_tolerates_missing_files(tmp_path: Path) -> None:
    results_dir = tmp_path / "results"

    compare_results._clear_results("a.pdf", results_dir=results_dir)

    assert (results_dir / "md").is_dir()
    assert (results_dir / "data").is_dir()
