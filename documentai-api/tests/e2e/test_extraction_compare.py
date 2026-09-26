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
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import boto3
import pytest
import requests

from documentai_api.config.env import get_env_config

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
_FIXTURES_DIR = Path(__file__).parent.parent / "helpers" / "fixtures" / "test-documents"
TEST_DOCS_DIR = _FIXTURES_DIR / "happy-path"

_EXTRACT_COMPARE_ADMIN_EMAIL = "extract-compare-admin@internal.invalid"
_EXPECTED_DIR = _FIXTURES_DIR / "expected"
_RESULTS_DIR = Path(__file__).parent / "results" / "extraction_compare"
_NO_VALUE = "-"
_INDICATOR_MAP = {"✅": "=", "🟡": "~", "❌": "x", "": "-"}


def _compare_prereqs_missing() -> bool:
    cfg = get_env_config()
    return not (cfg.cognito_client_id and cfg.ssm_prefix)


pytestmark = pytest.mark.skipif(
    _compare_prereqs_missing(),
    reason="COGNITO_CLIENT_ID and SSM_PREFIX must be set",
)


def _load_expected(filename: str) -> dict[str, str] | None:
    path = _EXPECTED_DIR / f"{Path(filename).stem}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return {k: str(v) if v is not None else _NO_VALUE for k, v in data.get("fields", {}).items()}


def _compare_files() -> list[str]:
    cases = json.loads((_FIXTURES_DIR / "expected.json").read_text())
    return [
        Path(filename).name
        for filename, entry in cases.items()
        if entry.get("compareEnabled", False)
    ]


_COMPARE_FILES = _compare_files()


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
    file_path: Path, jwt: str, timeout: int = 120, interval: int = 10
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


@pytest.mark.parametrize("filename", _COMPARE_FILES)
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


def _write_comparison_sidecar(filename: str, data: dict[str, Any]) -> None:
    sidecar = {
        "filename": filename,
        "primary_method": data.get("primaryMethod", "bda"),
        "durations": {
            method: float(d["extractionDurationSeconds"])
            if d.get("extractionDurationSeconds") is not None
            else None
            for method, d in (data.get("durations") or {}).items()
        },
        "cost": data.get("cost") or {},
        "cost_by_reason": data.get("costByReason") or {},
    }
    (_RESULTS_DIR / f"{Path(filename).stem}.data.json").write_text(
        json.dumps(sidecar, default=float)
    )


def _write_comparison_md(
    filename: str, data: dict[str, Any], expected: dict[str, str] | None
) -> None:
    _write_comparison_sidecar(filename, data)

    primary_method = data.get("primaryMethod", "primary")
    primary = data.get("primary", {})
    llm = data.get("llm", {})
    durations = data.get("durations", {})
    all_fields = sorted(
        set(primary) | set(llm) | (set(expected) if expected is not None else set())
    )

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

    cost = data.get("cost", {})
    tokens = data.get("tokens", {})
    cost_by_reason = data.get("costByReason") or {}
    pages = data.get("pages", 1)

    if cost or tokens:
        lines.append("**Cost**")
        lines.append("")
        lines.append("_By Service_")
        for model_id, entry_cost in cost.items():
            t = tokens.get(model_id, {})
            if t:
                lines.append(
                    f"- {model_id}: ${entry_cost:.8f} ({t.get('inputTokens', 0)} in / {t.get('outputTokens', 0)} out)"
                )
            else:
                lines.append(f"- {model_id}: ${entry_cost:.8f} ({pages} page(s))")
        lines.append(f"- **total: ${sum(cost.values()):.8f}**")

        if cost_by_reason:
            lines.append("")
            lines.append("_By Extraction Method_")
            lines.append(f"- shared (preclassification): ${cost_by_reason.get('shared', 0.0):.8f}")
            lines.append(f"- llm extraction: ${cost_by_reason.get('llmExtraction', 0.0):.8f}")
            lines.append(f"- primary ({primary_method}): ${cost_by_reason.get('primary', 0.0):.8f}")
            lines.append(f"- **total: ${sum(cost.values()):.8f}**")

        lines.append("")

    lines.append(
        f"| Field | Expected | {primary_method.upper()} Value | LLM (via Textract) Value | {primary_method.upper()} Conf | LLM Conf | {primary_method.upper()} Geometry | LLM Geometry | Geo Match |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for field in all_fields:
        p = primary.get(field, {})
        lm = llm.get(field, {})
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
        geo_match = _match_indicator(p_geo, llm_geo, tolerance=0.005)
        exp_val = expected.get(field, _NO_VALUE) if expected is not None else _NO_VALUE
        if expected is not None:
            p_cell = f"{_match_indicator(exp_val, p_val)} {p_val}".strip()
            llm_cell = f"{_match_indicator(exp_val, llm_val)} {llm_val}".strip()
        else:
            p_cell = p_val
            llm_cell = llm_val
        lines.append(
            f"| {field} | {exp_val} | {p_cell} | {llm_cell} | {p_conf} | {llm_conf} | {p_geo} | {llm_geo} | {geo_match} |"
        )
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results_file.write_text("\n".join(lines) + "\n")


def _print_comparison(filename: str, data: dict[str, Any], expected: dict[str, str] | None) -> None:
    primary_method = data.get("primaryMethod", "primary")
    primary = data.get("primary", {})
    llm = data.get("llm", {})
    durations = data.get("durations", {})
    all_fields = sorted(
        set(primary) | set(llm) | (set(expected) if expected is not None else set())
    )

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

    cost = data.get("cost", {})
    tokens = data.get("tokens", {})
    if cost or tokens:
        print("Cost:")
        for model_id, entry_cost in cost.items():
            t = tokens.get(model_id, {})
            print(
                f"  {model_id}: ${entry_cost:.8f} ({t.get('inputTokens', 0)} in / {t.get('outputTokens', 0)} out)"
            )
        print(f"  total: ${sum(cost.values()):.8f}")
        print()

    for field in all_fields:
        p = primary.get(field, {})
        lm = llm.get(field, {})
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
        exp_val = expected.get(field, _NO_VALUE) if expected is not None else _NO_VALUE
        if expected is not None:
            p_match = _INDICATOR_MAP[_match_indicator(exp_val, p_val)]
            llm_match = _INDICATOR_MAP[_match_indicator(exp_val, llm_val)]
            print(
                f"{field:<{col}} {exp_val:<20} {p_match} {p_val:<24} {llm_match} {llm_val:<24} {p_conf:>8}   {llm_conf:>8}"
            )
        else:
            print(
                f"{field:<{col}} {exp_val:<20} {p_val:<26} {llm_val:<26} {p_conf:>8}   {llm_conf:>8}"
            )

    print(sep)


def write_extraction_compare_summary(results_dir: Path) -> None:
    worker_files = sorted(
        (f for f in results_dir.glob("*.md") if f.name != "extraction_compare_summary.md"),
        key=lambda f: f.name,
    )
    if not worker_files:
        return

    duration_sums: dict[str, float] = defaultdict(float)
    duration_counts: dict[str, int] = defaultdict(int)
    cost_by_type: dict[str, float] = defaultdict(float)
    reason_totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    rows = []
    for md_file in worker_files:
        sidecar = results_dir / md_file.with_suffix(".data.json").name
        if not sidecar.exists():
            continue
        data = json.loads(sidecar.read_text())
        filename = data["filename"]
        primary_method = data.get("primary_method", "bda")
        file_cost = sum(data["cost"].values())
        for cost_key, amount in data["cost"].items():
            cost_by_type[cost_key] += amount
        for reason, amount in (data.get("cost_by_reason") or {}).items():
            reason_totals[primary_method][reason] += amount
        for method, secs in data["durations"].items():
            if secs is not None:
                duration_sums[method] += secs
                duration_counts[method] += 1
        rows.append(
            (
                filename,
                data["primary_method"],
                data["durations"],
                file_cost,
                data.get("cost_by_reason") or {},
            )
        )

    avg_durations = {
        method: duration_sums[method] / duration_counts[method] for method in duration_sums
    }

    run_ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines = ["# Extraction Compare Results\n", f"\n_Run: {run_ts}_\n"]

    if avg_durations:
        lines.append("\n**Avg Durations**\n")
        for method, avg in sorted(avg_durations.items()):
            lines.append(f"- {method}: {avg:.2f}s")
        lines.append("")

    if cost_by_type:
        total_cost = sum(cost_by_type.values())
        lines.append("\n**Total Cost by Model**\n")
        for cost_key, amount in sorted(cost_by_type.items()):
            lines.append(f"- {cost_key}: ${amount:.6f}")
        lines.append(f"- **total: ${total_cost:.6f}**")
        lines.append("")

    def _cost_compare_section(label: str, primary_method_key: str) -> list[str]:
        totals = reason_totals.get(primary_method_key)
        if not totals:
            return []
        shared = totals.get("shared", 0.0)
        primary = totals.get("primary", 0.0)
        llm = totals.get("llmExtraction", 0.0)
        out = [f"\n**{label}**\n"]
        out.append(f"- shared (preclassification): ${shared:.6f}")
        out.append(f"- {primary_method_key} extraction total: ${primary:.6f}")
        out.append(f"- LLM extraction total: ${llm:.6f}")
        out.append("")
        return out

    lines += _cost_compare_section("BDA vs LLM Cost (docs where primary=bda)", "bda")
    lines += _cost_compare_section("Textract vs LLM Cost (docs where primary=textract)", "textract")

    if rows:
        duration_methods = [m for m in sorted(avg_durations) if m != "textract"]
        duration_labels = [
            "Primary Duration" if m == "bda" else f"{m.upper()} Duration" for m in duration_methods
        ]
        headers = [
            "Document",
            "Method",
            "Total Cost",
            "Primary Cost",
            "LLM Cost",
            "Cost Delta",
            *duration_labels,
            "Duration Delta",
        ]
        lines.append("\n| " + " | ".join(headers) + " |")
        lines.append("|---" * len(headers) + "|")

        for filename, primary_method, durations, file_cost, cost_by_reason in rows:
            stem = Path(filename).stem
            link = f"[{filename}]({stem}.md)"
            primary_cost = cost_by_reason.get("primary", 0.0) + cost_by_reason.get("shared", 0.0)
            llm_cost = cost_by_reason.get("llmExtraction", 0.0)
            cost_delta = llm_cost - primary_cost
            primary_dur = durations.get("bda") or durations.get("textract")
            llm_dur = durations.get("llm")
            dur_delta = (
                f"{llm_dur - primary_dur:+.2f}s"
                if llm_dur is not None and primary_dur is not None
                else "-"
            )
            dur_cells = " | ".join(
                f"{durations.get(m):.2f}s" if durations.get(m) is not None else "-"
                for m in duration_methods
            )
            lines.append(
                f"| {link} | {primary_method} | ${file_cost:.6f} | ${primary_cost:.6f} | ${llm_cost:.6f} | {cost_delta:+.6f} | {dur_cells} | {dur_delta} |"
            )
        lines.append("")

    header = "".join(f"{line}\n" if not line.endswith("\n") else line for line in lines)

    summary = results_dir / "extraction_compare_summary.md"
    summary.write_text(header)
