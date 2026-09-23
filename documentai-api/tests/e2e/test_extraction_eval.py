"""E2E tests for /v1/admin/extraction-eval.

Requires a running API (BASE_URL) and AWS credentials with access to the
Cognito user pool and SSM parameter store. The extraction evaluator admin user and its password
are provisioned by Terraform (infra/environments/dev/main.tf).

Skipped automatically if COGNITO_CLIENT_ID or SSM_PREFIX are not set in the
environment.
"""

import os
import time
from pathlib import Path
from typing import Any

import boto3
import pytest
import requests

from documentai_api.config.env import get_env_config

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
TEST_DOCS_DIR = Path(__file__).parent.parent / "helpers" / "fixtures" / "test-documents"

_EXTRACT_EVAL_ADMIN_EMAIL = "extract-eval-admin@internal.invalid"


def _eval_prereqs_missing() -> bool:
    cfg = get_env_config()
    return not (cfg.cognito_client_id and cfg.ssm_prefix)


pytestmark = pytest.mark.skipif(
    _eval_prereqs_missing(),
    reason="COGNITO_CLIENT_ID and SSM_PREFIX must be set",
)

_EVAL_FILES = [
    "synthetic-public-benefits-identity-proof-state-photo-id.jpg",
    "synthetic-public-benefits-income-proof-pay-stub.jpg",
    "synthetic-snap-income-proof-employment-wage-verification-letter-rendered.png",
]


@pytest.fixture(scope="module")
def eval_jwt(reset_env, monkeypatch_session):
    """Fetch extraction evaluator admin password from SSM and exchange for a Cognito JWT."""
    for k, v in reset_env.items():
        monkeypatch_session.setenv(k, v)

    get_env_config.cache_clear()
    cfg = get_env_config()
    assert cfg.cognito_client_id
    password_param = f"{cfg.ssm_prefix}/extract-eval-admin-password"

    ssm = boto3.client("ssm")
    password = ssm.get_parameter(Name=password_param, WithDecryption=True)["Parameter"]["Value"]

    cognito = boto3.client("cognito-idp")
    response = cognito.initiate_auth(
        ClientId=cfg.cognito_client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": _EXTRACT_EVAL_ADMIN_EMAIL, "PASSWORD": password},
    )
    return response["AuthenticationResult"]["AccessToken"]


def _submit_and_poll(
    file_path: Path, jwt: str, timeout: int = 300, interval: int = 10
) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {jwt}"}

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
            return poll.json()  # type: ignore[no-any-return]
        assert poll.status_code == 404, f"unexpected status {poll.status_code}: {poll.text}"
        time.sleep(interval)

    pytest.fail(f"eval job {job_id} did not complete within {timeout}s")


@pytest.mark.parametrize("filename", _EVAL_FILES)
def test_extraction_eval(filename, eval_jwt):
    result = _submit_and_poll(TEST_DOCS_DIR / filename, eval_jwt)

    assert result["jobId"]
    assert isinstance(result["primary"], dict)
    assert isinstance(result["llm"], dict)
    assert result["primary"], "Primary extraction returned no fields"
    assert result["llm"], "LLM returned no fields"

    _print_comparison(filename, result)


def _print_comparison(filename: str, data: dict[str, Any]) -> None:
    primary_method = data.get("primaryMethod", "primary")
    primary = data.get("primary", {})
    llm = data.get("llm", {})
    all_fields = sorted(set(primary) | set(llm))

    col = 32
    p_label = f"{primary_method.upper()} Value"
    header = f"{'Field':<{col}} {p_label:<25} {'Conf':>8}   {'LLM Value':<25} {'LLM Conf':>8}"
    sep = "=" * len(header)

    print(f"\n{filename}")
    print(f"{sep}\n{header}\n{sep}")

    for field in all_fields:
        p = primary.get(field, {})
        lm = llm.get(field, {})
        p_val = str(p.get("value") or "—")[:24]
        llm_val = str(lm.get("value") or "—")[:24]
        p_conf = f"{p['confidence']:.2f}" if p.get("confidence") is not None else "—"
        llm_conf = f"{lm['confidence']:.4f}" if lm.get("confidence") is not None else "—"
        print(f"{field:<{col}} {p_val:<25} {p_conf:>8}   {llm_val:<25} {llm_conf:>8}")

    print(sep)
