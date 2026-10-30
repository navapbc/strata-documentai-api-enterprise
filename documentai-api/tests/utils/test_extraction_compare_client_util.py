"""Tests for submit_and_poll's handling of pending, failed, and complete results."""

from pathlib import Path
from typing import Any

import pytest

from documentai_api.models.extraction_compare import CompareDuration, CompareResponse
from documentai_api.utils import extraction_compare_client as client

_BASE = "https://api.example.test"
_MODULE = "documentai_api.utils.extraction_compare_client"


class _Response:
    def __init__(self, status_code: int, body: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self._body = body or {}
        self.text = str(self._body)

    def json(self) -> dict[str, Any]:
        return self._body


def _result(**flags: bool) -> _Response:
    return _Response(200, {"jobId": "job-1", "primaryMethod": "bda", **flags})


@pytest.fixture
def doc(tmp_path: Path) -> Path:
    path = tmp_path / "doc.pdf"
    path.write_bytes(b"%PDF-1.4")
    return path


@pytest.fixture
def no_sleep(mocker: Any) -> None:
    mocker.patch(f"{_MODULE}.time.sleep")


def _poll(mocker: Any, polls: list[_Response]) -> Any:
    mocker.patch(f"{_MODULE}.requests.post", return_value=_Response(202, {"jobId": "job-1"}))
    return mocker.patch(f"{_MODULE}.requests.get", side_effect=polls)


def test_keeps_polling_while_pending_then_returns_result(mocker, doc, no_sleep):
    get = _poll(
        mocker,
        [_result(isCompleted=False), _result(isCompleted=False), _result(isCompleted=True)],
    )

    result = client.submit_and_poll(_BASE, doc, "jwt")

    assert result.is_completed is True
    assert get.call_count == 3


def test_keeps_polling_on_404_until_found(mocker, doc, no_sleep):
    _poll(mocker, [_Response(404), _result(isCompleted=True)])

    assert client.submit_and_poll(_BASE, doc, "jwt").is_completed is True


def test_unexpected_status_raises(mocker, doc, no_sleep):
    _poll(mocker, [_Response(500)])

    with pytest.raises(RuntimeError, match="unexpected status 500"):
        client.submit_and_poll(_BASE, doc, "jwt")


def test_times_out_while_still_pending(mocker, doc, no_sleep):
    mocker.patch(f"{_MODULE}.requests.post", return_value=_Response(202, {"jobId": "job-1"}))
    mocker.patch(f"{_MODULE}.requests.get", return_value=_result(isCompleted=False))
    mocker.patch(f"{_MODULE}.time.monotonic", side_effect=[0, 1, 2, 999])

    with pytest.raises(client.ExtractionCompareTimeoutError):
        client.submit_and_poll(_BASE, doc, "jwt", timeout=10)


def test_match_icon_no_ground_truth_returns_no_expected():
    assert client.match_icon(client.NO_GROUND_TRUTH, "some value") == client.ICON_NO_EXPECTED


def test_match_icon_both_empty_returns_no_expected():
    assert (
        client.match_icon(client.EXPECTED_EMPTY, client.EXPECTED_EMPTY) == client.ICON_NO_EXPECTED
    )


def test_match_icon_exact_match():
    assert client.match_icon("foo", "foo") == client.ICON_EXACT


def test_match_icon_miss_when_received_empty():
    assert client.match_icon("foo", client.EXPECTED_EMPTY) == client.ICON_MISS


def _durations(**spans: tuple[str | None, str | None]) -> CompareResponse:
    return CompareResponse(
        job_id="job-1",
        primary_method="bda",
        durations={
            method: CompareDuration(processing_started_at=start, processing_completed_at=end)
            for method, (start, end) in spans.items()
        },
    )


def test_processing_span_covers_earliest_start_to_latest_completion():
    result = _durations(
        bda=("2026-10-30T02:31:00+00:00", "2026-10-30T02:31:25+00:00"),
        **{"ocr-mapping": ("2026-10-30T02:31:02+00:00", "2026-10-30T02:31:08+00:00")},
    )

    assert client.processing_span_seconds(result) == 25.0


def test_processing_span_is_none_without_timestamps():
    assert client.processing_span_seconds(_durations(bda=(None, None))) is None
    assert client.processing_span_seconds(_durations()) is None
