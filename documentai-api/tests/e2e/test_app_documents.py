import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from documentai_api.schemas.document_metadata import DocumentMetadata
from tests.helpers.fixtures.paths import TEST_DOCS_DIR

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
    skip_bda: bool = False


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
                    content_type=expected.get("contentType"),
                    required_fields_for_extraction=expected.get("requiredFieldsForExtraction"),
                    skip_bda=expected.get("skipBda", False),
                ),
            ),
            marks=(
                [pytest.mark.flaky(reruns=expected["rerunsOverride"])]
                if "rerunsOverride" in expected
                else []
            ),
            id=filename,
        )
        for filename, expected in cases.items()
        if expected.get("e2eEnabled", False)
    ]


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
def test_post_document(test_case, client, e2e_tenant_id):
    expected_result = test_case.expected_result

    with _extraction_rule_for(e2e_tenant_id, expected_result):
        body = client.upload_and_wait(test_case.file_path)

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

    # Password-protected, blurry, and multi-document docs short-circuit before BDA,
    # so BDA output and the processed-date timestamp are never written. skip_bda
    # covers the same case for no-category-matched docs with no default BDA project
    # configured (see resolve_project_arn) - the resulting responseCode (002) is
    # otherwise identical to a BDA run that found no matching blueprint.
    short_circuits_before_bda = (
        expected_result.is_blurry
        or expected_result.is_password_protected
        or expected_result.response_code in {"400", "401"}
        or expected_result.skip_bda
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
