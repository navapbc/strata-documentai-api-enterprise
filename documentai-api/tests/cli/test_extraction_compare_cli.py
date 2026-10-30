"""Tests for extraction compare CLI utilities."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from documentai_api.cli.extraction_compare._types import _ResultData
from documentai_api.cli.extraction_compare.comparison import _sidecar_completed_at


def test_sidecar_completed_at_prefers_stored_value(tmp_path: Path) -> None:
    sidecar = tmp_path / "doc.data.json"
    sidecar.write_text("{}")
    stored = "2026-10-28T15:13:22+00:00"

    result = _sidecar_completed_at(sidecar, {_ResultData.COMPLETED_AT: stored})

    assert result == datetime(2026, 10, 28, 15, 13, 22, tzinfo=UTC)


def test_sidecar_completed_at_falls_back_to_mtime_for_legacy_files(tmp_path: Path) -> None:
    sidecar = tmp_path / "doc.data.json"
    sidecar.write_text(json.dumps({"filename": "doc.pdf"}))
    mtime = datetime(2026, 10, 1, 2, 38, tzinfo=UTC)
    os.utime(sidecar, (mtime.timestamp(), mtime.timestamp()))

    assert _sidecar_completed_at(sidecar, {"filename": "doc.pdf"}) == mtime
