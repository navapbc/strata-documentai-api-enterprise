"""E2E tests for /v1/admin/extraction-eval.

Requires:
  - A running API (BASE_URL)
  - EVAL_JWT env var set to a valid admin JWT

Skipped automatically if EVAL_JWT is not set.
"""

import os
import time
from pathlib import Path

import pytest
import requests

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
EVAL_JWT = os.getenv("EVAL_JWT")
TEST_DOCS_DIR = Path(__file__).parent.parent / "helpers" / "fixtures" / "test-documents"

pytestmark = pytest.mark.skipif(not EVAL_JWT, reason="EVAL_JWT not set")

_EVAL_FILES = [
    "synthetic-public-benefits-identity-proof-state-photo-id.jpg",
    "synthetic-public-benefits-income-proof-pay-stub.jpg",
    "synthetic-snap-income-proof-employment-wage-verification-letter-rendered.png",
]


def _submit_and_poll(file_path: Path, timeout: int = 300, interval: int = 10) -> dict:
    headers = {"Authorization": f"Bearer {EVAL_JWT}"}

    with file_path.open("rb") as f:
        response = requests.post(
            f"{BASE_URL}/v1/admin/extraction-eval",
            headers=headers,
            files={"file": (file_path.name, f)},
            timeout=30,
        )
    assert response.status_code == 202, f"submit failed {response.status_code}: {response.text}"
    job_id = response.json()["jobId"]

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        poll = requests.get(
            f"{BASE_URL}/v1/admin/extraction-eval/{job_id}",
            headers=headers,
            timeout=30,
        )
        if poll.status_code == 200:
            return poll.json()
        assert poll.status_code == 404, f"unexpected status {poll.status_code}: {poll.text}"
        time.sleep(interval)

    pytest.fail(f"eval job {job_id} did not complete within {timeout}s")


@pytest.mark.parametrize("filename", _EVAL_FILES)
def test_extraction_eval(filename):
    result = _submit_and_poll(TEST_DOCS_DIR / filename)

    assert result["jobId"]
    assert isinstance(result["bda"], dict)
    assert isinstance(result["llm"], dict)
    assert result["bda"], "BDA returned no fields"
    assert result["llm"], "LLM returned no fields"

    _print_comparison(filename, result)


def _print_comparison(filename: str, data: dict) -> None:
    bda = data.get("bda", {})
    llm = data.get("llm", {})
    all_fields = sorted(set(bda) | set(llm))

    col = 32
    header = f"{'Field':<{col}} {'BDA Value':<25} {'BDA Conf':>8}   {'LLM Value':<25} {'LLM Conf':>8}"
    sep = "=" * len(header)

    print(f"\n{filename}")
    print(f"{sep}\n{header}\n{sep}")

    for field in all_fields:
        b = bda.get(field, {})
        lm = llm.get(field, {})
        bda_val = str(b.get("value") or "—")[:24]
        llm_val = str(lm.get("value") or "—")[:24]
        bda_conf = f"{b['confidence']:.2f}" if b.get("confidence") is not None else "—"
        llm_conf = f"{lm['confidence']:.4f}" if lm.get("confidence") is not None else "—"
        print(f"{field:<{col}} {bda_val:<25} {bda_conf:>8}   {llm_val:<25} {llm_conf:>8}")

    print(sep)
