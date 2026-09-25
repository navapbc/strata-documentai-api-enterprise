"""E2E tests for /v1/admin/extraction-compare.

Requires a running API (BASE_URL) and AWS credentials with access to the
Cognito user pool and SSM parameter store. The extraction compare admin user and its password
are provisioned by Terraform (infra/environments/dev/main.tf).

Skipped automatically if COGNITO_CLIENT_ID or SSM_PREFIX are not set in the
environment.
"""

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import boto3
import pytest
import requests

from documentai_api.config.env import get_env_config

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
TEST_DOCS_DIR = (
    Path(__file__).parent.parent / "helpers" / "fixtures" / "test-documents" / "happy-path"
)

_EXTRACT_COMPARE_ADMIN_EMAIL = "extract-compare-admin@internal.invalid"


def _compare_prereqs_missing() -> bool:
    cfg = get_env_config()
    return not (cfg.cognito_client_id and cfg.ssm_prefix)


pytestmark = pytest.mark.skipif(
    _compare_prereqs_missing(),
    reason="COGNITO_CLIENT_ID and SSM_PREFIX must be set",
)

_EXPECTED_DIR = Path(__file__).parent / "expected" / "extraction_compare"
_RESULTS_DIR = Path(__file__).parent / "results" / "extraction_compare"
_NO_VALUE = "-"
_INDICATOR_MAP = {"✅": "=", "🟡": "~", "❌": "x", "": "-"}


def _load_expected(filename: str) -> dict[str, str]:
    path = _EXPECTED_DIR / f"{Path(filename).stem}.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return {k: str(v) if v is not None else _NO_VALUE for k, v in data.get("fields", {}).items()}


_EVAL_FILES = [
    "synthetic-public-benefits-identity-proof-state-photo-id.jpg",
    "synthetic-public-benefits-income-proof-pay-stub.jpg",
    "synthetic-snap-income-proof-employment-wage-verification-letter-rendered.png",
]


@pytest.fixture(scope="session")
def compare_jwt(reset_env):
    """Fetch extraction compare admin password from SSM and exchange for a Cognito JWT."""
    os.environ.update(reset_env)
    get_env_config.cache_clear()
    cfg = get_env_config()
    assert cfg.cognito_client_id
    password_param = f"{cfg.ssm_prefix}/extract-compare-admin-password"

    ssm = boto3.client("ssm")
    password = ssm.get_parameter(Name=password_param, WithDecryption=True)["Parameter"]["Value"]

    cognito = boto3.client("cognito-idp")
    response = cognito.initiate_auth(
        ClientId=cfg.cognito_client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": _EXTRACT_COMPARE_ADMIN_EMAIL, "PASSWORD": password},
    )
    return response["AuthenticationResult"]["AccessToken"]


def _submit_and_poll(
    file_path: Path, jwt: str, timeout: int = 60, interval: int = 10
) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {jwt}"}

    with file_path.open("rb") as f:
        response = requests.post(
            f"{BASE_URL}/v1/admin/extraction-compare",
            headers=headers,
            files={"file": (file_path.name, f)},
            timeout=30,
        )
    assert response.status_code == 202, f"submit failed {response.status_code}: {response.text}"
    job_id = response.json()["jobId"]

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        poll = requests.get(
            f"{BASE_URL}/v1/admin/extraction-compare/{job_id}",
            headers=headers,
            timeout=30,
        )
        if poll.status_code == 200:
            return poll.json()  # type: ignore[no-any-return]
        assert poll.status_code == 404, f"unexpected status {poll.status_code}: {poll.text}"
        time.sleep(interval)

    pytest.fail(f"compare job {job_id} did not complete within {timeout}s")


@pytest.mark.parametrize("filename", _EVAL_FILES)
def test_extraction_compare(filename, compare_jwt):
    result = _submit_and_poll(TEST_DOCS_DIR / filename, compare_jwt)

    assert result["jobId"]
    assert isinstance(result["primary"], dict)
    assert isinstance(result["llm"], dict)
    assert result["primary"], "Primary extraction returned no fields"
    assert result["llm"], "LLM returned no fields"

    _print_comparison(filename, result, _load_expected(filename))
    _write_comparison_md(filename, result, _load_expected(filename))


def _fmt_geometry(geo: list[dict[str, Any]] | None) -> str:
    if not geo:
        return _NO_VALUE
    bb = geo[0].get("boundingBox") or geo[0]
    left, top, w, h = bb.get("left", 0), bb.get("top", 0), bb.get("width", 0), bb.get("height", 0)
    return f"{left:.3f},{top:.3f},{w:.3f},{h:.3f}"


def _normalize_value(v: str) -> str:
    """Normalize a field value for loose equality comparison."""
    import re

    v = v.strip().lower()
    v = re.sub(r"[\$,]", "", v)  # strip currency symbols and commas
    v = re.sub(r"\.0+$", "", v)  # strip trailing .00 / .0
    # normalize common date formats to yyyy-mm-dd
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", v)
    if m:
        v = f"{m.group(3)}-{m.group(1)}-{m.group(2)}"
    # normalize boolean synonyms
    v = {"yes": "true", "no": "false"}.get(v, v)
    return v


def _match_indicator(expected: str, received: str, tolerance: float = 0.0) -> str:
    if expected in ("—", _NO_VALUE) and received in ("—", _NO_VALUE):
        return ""

    if expected in ("—", _NO_VALUE) or received in ("—", _NO_VALUE):
        return "❌"

    if expected == received:
        return "✅"

    if tolerance:
        try:
            if all(
                abs(float(a) - float(b)) <= tolerance
                for a, b in zip(expected.split(","), received.split(","), strict=False)
            ):
                return "🟡"
        except ValueError:
            pass

    if _normalize_value(expected) == _normalize_value(received):
        return "🟡"

    try:
        if float(expected) == float(received):
            return "🟡"
    except ValueError:
        pass

    return "❌"


def _write_comparison_md(filename: str, data: dict[str, Any], expected: dict[str, str]) -> None:
    primary_method = data.get("primaryMethod", "primary")
    primary = data.get("primary", {})
    llm = data.get("llm", {})
    durations = data.get("durations", {})
    all_fields = sorted(set(primary) | set(llm) | set(expected))

    results_file = _RESULTS_DIR / f"{Path(filename).stem}.md"

    lines = [f"_Run: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}_\n", f"\n## {filename}\n"]

    if durations:
        lines.append("**Durations**\n")
        for method, d in durations.items():
            extraction = d.get("extractionDurationSeconds", _NO_VALUE)
            bda_invoke = d.get("bdaInvocationDurationSeconds")
            line = f"- {method}: {extraction}s extraction"
            if bda_invoke is not None:
                line += f", {bda_invoke}s BDA invocation"
            lines.append(line)
        lines.append("")

    lines.append(
        f"| Field | Expected | {primary_method.upper()} Value | LLM (via Textract) Value | {primary_method.upper()} Conf | LLM Conf | {primary_method.upper()} Geometry | LLM Geometry | Geo Match |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for field in all_fields:
        p = primary.get(field, {})
        lm = llm.get(field, {})
        exp_val = expected.get(field, _NO_VALUE)
        p_val = str(p.get("value") or _NO_VALUE)
        llm_val = str(lm.get("value") or _NO_VALUE)
        p_conf = f"{p['confidence']:.2f}" if p.get("confidence") is not None else _NO_VALUE
        llm_conf_raw = lm.get("confidence")
        llm_conf = (
            "N/A"
            if llm_conf_raw == 0.0
            else f"{llm_conf_raw:.4f}"
            if llm_conf_raw is not None
            else _NO_VALUE
        )
        p_geo = _fmt_geometry(p.get("geometry"))
        llm_geo = _fmt_geometry(lm.get("geometry"))
        p_match = _match_indicator(exp_val, p_val)
        llm_match = _match_indicator(exp_val, llm_val)
        geo_match = _match_indicator(p_geo, llm_geo, tolerance=0.005)
        p_cell = f"{p_match} {p_val}".strip()
        llm_cell = f"{llm_match} {llm_val}".strip()
        lines.append(
            f"| {field} | {exp_val} | {p_cell} | {llm_cell} | {p_conf} | {llm_conf} | {p_geo} | {llm_geo} | {geo_match} |"
        )
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results_file.write_text("\n".join(lines) + "\n")


def _print_comparison(filename: str, data: dict[str, Any], expected: dict[str, str]) -> None:
    primary_method = data.get("primaryMethod", "primary")
    primary = data.get("primary", {})
    llm = data.get("llm", {})
    durations = data.get("durations", {})
    all_fields = sorted(set(primary) | set(llm) | set(expected))

    col = 32
    p_label = f"{primary_method.upper()} Value"
    header = f"{'Field':<{col}} {'Expected':<20} {p_label:<26} {'LLM (via Textract)':<26} {'Conf':>8}   {'LLM Conf':>8}"
    sep = "=" * len(header)

    print(f"\n{filename}")
    print(f"{sep}\n{header}\n{sep}")

    if durations:
        for method, d in durations.items():
            extraction = d.get("extractionDurationSeconds", _NO_VALUE)
            bda_invoke = d.get("bdaInvocationDurationSeconds")
            line = f"  {method}: {extraction}s extraction"
            if bda_invoke is not None:
                line += f", {bda_invoke}s BDA invocation"
            print(line)
        print()

    for field in all_fields:
        p = primary.get(field, {})
        lm = llm.get(field, {})
        exp_val = expected.get(field, _NO_VALUE)
        p_val = str(p.get("value") or _NO_VALUE)
        llm_val = str(lm.get("value") or _NO_VALUE)
        p_conf = f"{p['confidence']:.2f}" if p.get("confidence") is not None else _NO_VALUE
        llm_conf_raw = lm.get("confidence")
        llm_conf = (
            "N/A"
            if llm_conf_raw == 0.0
            else f"{llm_conf_raw:.4f}"
            if llm_conf_raw is not None
            else _NO_VALUE
        )
        p_match = _INDICATOR_MAP[_match_indicator(exp_val, p_val)]
        llm_match = _INDICATOR_MAP[_match_indicator(exp_val, llm_val)]
        print(
            f"{field:<{col}} {exp_val:<20} {p_match} {p_val:<24} {llm_match} {llm_val:<24} {p_conf:>8}   {llm_conf:>8}"
        )

    print(sep)
