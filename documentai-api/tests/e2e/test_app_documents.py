import json
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    required_fields_for_extraction: list[str] | None = None


@dataclass
class Case:
    file_path: Path
    expected_result: ExpectedResult


def load_test_cases() -> list[Any]:
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
                    required_fields_for_extraction=expected.get("requiredFieldsForExtraction"),
                ),
            ),
            marks=(
                [pytest.mark.flaky(reruns=expected["reruns_override"])]
                if "reruns_override" in expected
                else []
            ),
            id=filename,
        )
        for filename, expected in cases.items()
        if expected.get("e2e_enabled", False)
    ]


def _upload_and_wait(
    base_url: str, api_key: str, file_path: Path, timeout: int = 75, interval: int = 2
) -> dict[str, Any]:
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
            return body  # type: ignore[no-any-return]

        time.sleep(interval)

    pytest.fail(f"job {job_id} did not complete within {timeout}s")


@contextmanager
def _extraction_rule_for(tenant_id: str, expected: ExpectedResult) -> Iterator[None]:
    """Seed the per-case extraction rule (if any) for the duration of an upload.

    Fixtures that need a specific document type/field combination to trip
    MISSING_FIELDS (101) declare a "requiredFieldsForExtraction" list in
    expected.json. Because extraction rules are keyed by (tenant, document_type),
    seeding one rule per case immediately around the upload - rather than once
    per unique document class up front - lets multiple fixtures share a document
    class while each asserts against its own required-field set. The rule is torn
    down afterward even if the upload fails.
    """
    from documentai_api.utils.extraction_rules import delete_rule, upsert_rule

    required_fields = expected.required_fields_for_extraction
    document_type = expected.bda_matched_document_class

    if required_fields and document_type:
        upsert_rule(tenant_id, document_type, required_fields, optional_fields=[])
        try:
            yield
        finally:
            delete_rule(tenant_id, document_type)
    else:
        yield


@pytest.mark.parametrize("test_case", load_test_cases())
def test_post_document(test_case, base_url, api_key, e2e_tenant_id):
    expected_result = test_case.expected_result

    with _extraction_rule_for(e2e_tenant_id, expected_result):
        body = _upload_and_wait(base_url, api_key, test_case.file_path)

    from documentai_api.config.env import get_env_config
    from documentai_api.services import ddb as ddb_service

    table_name = get_env_config().documentai_document_metadata_table_name
    job_id_index_name = get_env_config().documentai_document_metadata_job_id_index_name

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
    items = ddb_service.query_by_key(
        table_name or "", job_id_index_name or "", DocumentMetadata.JOB_ID, job_id
    )
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
