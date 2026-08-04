import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import pytest
import requests

from documentai_api.schemas.document_metadata import DocumentMetadata

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
TEST_DOCS_DIR = Path(__file__).parent.parent / "helpers" / "fixtures" / "test-documents"
CLASSIFICATIONS = TEST_DOCS_DIR / "expected.json"


@dataclass
class ExpectedResult:
    preclassification_category: str | None
    response_code: str
    is_blurry: bool = False
    is_password_protected: bool = False
    bda_matched_document_class: str | None = None
    content_type: str | None = None


@dataclass
class Case:
    file_path: Path
    expected_result: ExpectedResult


def load_test_cases() -> list[Case]:
    cases = json.loads(CLASSIFICATIONS.read_text())
    return [
        pytest.param(
            Case(
                file_path=TEST_DOCS_DIR / filename,
                expected_result=ExpectedResult(
                    preclassification_category=expected["preclassificationCategory"],
                    response_code=expected["responseCode"],
                    is_blurry=expected.get("isDocumentBlurry", False),
                    is_password_protected=expected.get("isPasswordProtected", False),
                    bda_matched_document_class=expected.get("bdaMatchedDocumentClass"),
                    content_type=expected.get("content_type"),
                ),
            ),
            marks=[pytest.mark.flaky(reruns=expected.get("reruns_override", 0))],
            id=filename,
        )
        for filename, expected in cases.items()
        if expected.get("e2e_enabled", False)
    ]


def _upload_and_wait(base_url, api_key, file_path, timeout=60, interval=2):
    with file_path.open("rb") as f:
        response = requests.post(
            f"{base_url}/v1/documents",
            headers={"API-Key": api_key},
            files={"file": f},
            timeout=30,
        )
    assert response.status_code == 202, f"upload failed {response.status_code}: {response.text}"
    job_id = response.json()["jobId"]

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        r = requests.get(
            f"{base_url}/v1/documents/{job_id}",
            headers={"API-Key": api_key},
            timeout=30,
        )
        assert r.status_code == 200, f"poll failed {r.status_code}: {r.text}"
        body = r.json()

        # responseCode is always present in the serialized response (it's an
        # optional model field that defaults to null during processing). It only
        # becomes non-null once the v1 response is persisted, i.e. the job is
        # done - including terminal states that never invoke BDA (password
        # protected, blurry), where completedAt is never set.
        if body.get("responseCode") is not None:
            return body

        time.sleep(interval)

    pytest.fail(f"job {job_id} did not complete within {timeout}s")


@pytest.mark.parametrize("test_case", load_test_cases())
def test_post_document(test_case, base_url, api_key):
    body = _upload_and_wait(base_url, api_key, test_case.file_path)
    expected_result = test_case.expected_result

    from documentai_api.config.env import get_aws_config
    from documentai_api.services import ddb as ddb_service

    table_name = get_aws_config().documentai_document_metadata_table_name
    job_id_index_name = get_aws_config().documentai_document_metadata_job_id_index_name

    expect: dict[str, str | bool | None] = {
        DocumentMetadata.BDA_MATCHED_DOCUMENT_CLASS: expected_result.bda_matched_document_class,
        DocumentMetadata.RESPONSE_CODE: expected_result.response_code,
        DocumentMetadata.IS_DOCUMENT_BLURRY: expected_result.is_blurry,
        DocumentMetadata.IS_PASSWORD_PROTECTED: expected_result.is_password_protected,
        DocumentMetadata.CONTENT_TYPE: expected_result.content_type,
    }

    expect_not_none: list[str] = [
        DocumentMetadata.V1_API_RESPONSE_JSON,
        DocumentMetadata.UPDATED_AT,
        DocumentMetadata.CREATED_AT,
    ]

    if expected_result.preclassification_category is not None:
        expect_not_none.append(DocumentMetadata.PRECLASSIFICATION_CATEGORY)

    # Password-protected, blurry, and multi-document docs short-circuit before BDA, so BDA
    # output and the processed-date timestamp are never written.
    short_circuits_before_bda = (
        expected_result.is_blurry
        or expected_result.is_password_protected
        or expected_result.response_code in {"400", "401"}
    )
    if not short_circuits_before_bda:
        expect_not_none += [
            DocumentMetadata.BDA_OUTPUT_S3_URI,
            DocumentMetadata.PROCESSED_DATE,
        ]

    job_id = body["jobId"]
    items = ddb_service.query_by_key(table_name, job_id_index_name, DocumentMetadata.JOB_ID, job_id)
    assert items is not None, f"no record found in DDB for jobId {job_id}"
    assert len(items) == 1, (
        f"expected exactly 1 record in DDB for jobId {job_id} but found {len(items)}"
    )
    record = items[0]

    for field in expect_not_none:
        assert record.get(field) is not None, f"{field} should not be null in DDB record"

    for field, expected_value in expect.items():
        if expected_value is None:
            assert record.get(field) is None, f"{field} should be null in DDB record"
            continue

        actual_value = record.get(field)

        assert actual_value == expected_value, (
            f"file {test_case.file_path.name}, expected {field} to be {expected_value} but got {actual_value}"
        )
