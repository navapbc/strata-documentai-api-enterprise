"""Shared client for calling /v1/admin/extraction-compare and formatting field results.

Used by the run-extraction-compare CLI (documentai_api.cli.run_extraction_compare).
"""

import difflib
import re
import secrets
import time
from collections.abc import Generator
from contextlib import contextmanager, suppress
from datetime import datetime
from pathlib import Path

import boto3
import requests

from documentai_api.models.extraction_compare import CompareFieldResult, CompareResponse

EXPECTED_EMPTY = "-"
NO_GROUND_TRUTH = "N/A"
NO_VALUE = EXPECTED_EMPTY  # backwards compat alias
ICON_EXACT = "✅"
ICON_APPROX = "🟡"
ICON_MISS = "❌"
ICON_NO_EXPECTED = ""
INDICATOR_MAP = {ICON_EXACT: "=", ICON_APPROX: "~", ICON_MISS: "x", ICON_NO_EXPECTED: "-"}
APPROX_SIMILARITY_THRESHOLD = 0.8


class ExtractionCompareTimeoutError(Exception):
    """Raised when a compare job doesn't complete within the poll timeout."""


@contextmanager
def cognito_jwt(
    user_pool_id: str,
    client_id: str,
    region: str = "us-east-1",
) -> Generator[str, None, None]:
    """Create a temporary super-admin Cognito user, yield its JWT, then delete the user."""
    cognito = boto3.client("cognito-idp", region_name=region)
    username = f"e2e-admin-{secrets.token_hex(4)}@example.com"
    password = secrets.token_urlsafe(16) + "!1Aa"

    cognito.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[
            {"Name": "email", "Value": username},
            {"Name": "email_verified", "Value": "true"},
        ],
        MessageAction="SUPPRESS",
    )
    try:
        cognito.admin_set_user_password(
            UserPoolId=user_pool_id, Username=username, Password=password, Permanent=True
        )
        cognito.admin_add_user_to_group(
            UserPoolId=user_pool_id, Username=username, GroupName="super-admin"
        )
        resp = cognito.initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
            ClientId=client_id,
        )
        yield resp["AuthenticationResult"]["IdToken"]
    finally:
        with suppress(Exception):
            cognito.admin_delete_user(UserPoolId=user_pool_id, Username=username)


def submit_and_poll(
    base_url: str, file_path: Path, jwt: str, timeout: int = 120, interval: int = 5
) -> CompareResponse:
    """Submit a file to the extraction-compare endpoint and poll until complete."""
    headers = {"Authorization": f"Bearer {jwt}"}

    with file_path.open("rb") as f:
        response = requests.post(
            f"{base_url}/v1/admin/extraction-compare",
            headers=headers,
            files={"file": (file_path.name, f)},
            timeout=30,
        )

    if response.status_code != 202:
        raise RuntimeError(f"submit failed {response.status_code}: {response.text}")
    job_id = response.json()["jobId"]

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        poll = requests.get(
            f"{base_url}/v1/admin/extraction-compare/{job_id}",
            headers=headers,
            timeout=30,
        )
        if poll.status_code == 200:
            result = CompareResponse.model_validate(poll.json())
            if not result.is_completed:
                time.sleep(interval)
                continue
            return result
        if poll.status_code != 404:
            raise RuntimeError(f"unexpected status {poll.status_code}: {poll.text}")
        time.sleep(interval)

    raise ExtractionCompareTimeoutError(f"compare job {job_id} did not complete within {timeout}s")


def processing_span_seconds(result: CompareResponse) -> float | None:
    """Return the server-side window from the earliest processing start to the latest completion.

    Uses the per-method timestamps the API reports, so it is not affected by poll granularity.
    Returns None if the response doesn't carry them.
    """
    starts = [d.processing_started_at for d in result.durations.values() if d.processing_started_at]
    ends = [
        d.processing_completed_at for d in result.durations.values() if d.processing_completed_at
    ]
    if not starts or not ends:
        return None

    try:
        first = min(datetime.fromisoformat(s) for s in starts)
        last = max(datetime.fromisoformat(e) for e in ends)
    except (ValueError, TypeError):
        return None

    return (last - first).total_seconds()


def field_display_values(
    p: CompareFieldResult,
    lm: CompareFieldResult,
    expected: dict[str, str] | None,
    field: str,
) -> tuple[str, str, str, str, str]:
    """Return (p_val, llm_val, p_conf, llm_conf, exp_val) formatted for display."""
    p_val = str(p.value or EXPECTED_EMPTY)
    llm_val = str(lm.value or EXPECTED_EMPTY)
    p_conf = f"{p.confidence:.2f}" if p.confidence is not None else EXPECTED_EMPTY

    llm_conf = (
        "N/A"
        if lm.confidence == 0.0
        else f"{lm.confidence:.4f}"
        if lm.confidence is not None
        else EXPECTED_EMPTY
    )

    exp_val = expected.get(field, NO_GROUND_TRUTH) if expected is not None else NO_GROUND_TRUTH
    return p_val, llm_val, p_conf, llm_conf, exp_val


def normalize_value(v: str) -> str:
    """Normalize a field value for loose equality comparison."""
    v = v.strip().lower()
    v = re.sub(r"[\$,]", "", v)  # strip currency symbols and commas
    v = re.sub(r"\.0+$", "", v)  # strip trailing .00 / .0

    # normalize common date formats to yyyy-mm-dd
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", v)
    if m:
        v = f"{m.group(3)}-{m.group(1)}-{m.group(2)}"

    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{2})", v)
    if m:
        v = f"20{m.group(3)}-{m.group(1)}-{m.group(2)}"

    # normalize boolean synonyms
    v = {"yes": "true", "no": "false"}.get(v, v)
    return v


def match_icon(expected: str, received: str, tolerance: float = 0.0, field_name: str = "") -> str:
    """Return an icon indicating exact, approximate, or no match. Tolerance applies to numeric geo coordinates."""
    if expected == NO_GROUND_TRUTH:
        return ICON_NO_EXPECTED

    if expected == EXPECTED_EMPTY and received == EXPECTED_EMPTY:
        return ICON_NO_EXPECTED

    if received == EXPECTED_EMPTY:
        return ICON_MISS

    if expected == EXPECTED_EMPTY:
        return ICON_MISS

    if expected == received:
        return ICON_EXACT

    norm_e, norm_r = normalize_value(expected), normalize_value(received)

    if norm_e == norm_r:
        return ICON_EXACT

    if tolerance:
        try:
            if all(
                abs(float(a) - float(b)) <= tolerance
                for a, b in zip(expected.split(","), received.split(","), strict=False)
            ):
                return ICON_EXACT
        except ValueError:
            pass

    try:
        if float(norm_e) == float(norm_r):
            return ICON_EXACT
    except ValueError:
        pass

    if difflib.SequenceMatcher(None, norm_e, norm_r).ratio() >= APPROX_SIMILARITY_THRESHOLD:
        return ICON_APPROX

    return ICON_MISS


def print_comparison(
    filename: str, result: CompareResponse, expected: dict[str, str] | None
) -> None:
    """Print a field-by-field comparison table to stdout."""
    primary_method = result.primary_method
    all_fields = sorted(
        set(result.primary)
        | set(result.ocr_mapping)
        | (set(expected) if expected is not None else set())
    )

    col = 32
    p_label = f"{primary_method.upper()} Value"
    header = f"{'Field':<{col}} {'Expected':<20} {p_label:<26} {'LLM (via Textract)':<26} {'Conf':>8}   {'LLM Conf':>8}"
    sep = "=" * len(header)

    print(f"\n{filename}")
    print(f"{sep}\n{header}\n{sep}")

    for method, d in result.durations.items():
        line = f"  {method}: {d.extraction_duration_seconds}s extraction"
        if d.bda_invocation_duration_seconds is not None:
            line += f", {d.bda_invocation_duration_seconds}s BDA invocation"
        print(line)

    if result.durations:
        print()

    if result.cost or result.tokens:
        print("Cost:")
        for model_id, entry_cost in result.cost.items():
            t = result.tokens.get(model_id, {})
            print(
                f"  {model_id}: ${entry_cost:.8f} ({t.get('inputTokens', 0)} in / {t.get('outputTokens', 0)} out)"
            )
        print(f"  total: ${sum(result.cost.values()):.8f}")
        print()

    for field in all_fields:
        p = result.primary.get(field, CompareFieldResult())
        lm = result.ocr_mapping.get(field, CompareFieldResult())
        p_val, llm_val, p_conf, llm_conf, exp_val = field_display_values(p, lm, expected, field)
        if expected is not None:
            p_match = INDICATOR_MAP[match_icon(exp_val, p_val, field_name=field)]
            llm_match = INDICATOR_MAP[match_icon(exp_val, llm_val, field_name=field)]
            print(
                f"{field:<{col}} {exp_val:<20} {p_match} {p_val:<24} {llm_match} {llm_val:<24} {p_conf:>8}   {llm_conf:>8}"
            )
        else:
            print(
                f"{field:<{col}} {exp_val:<20} {p_val:<26} {llm_val:<26} {p_conf:>8}   {llm_conf:>8}"
            )

    print(sep)
