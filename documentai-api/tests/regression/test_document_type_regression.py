"""Regression suite: re-run every known document type against a canned BDA result.

Run via `make test-regression`. Each case in document_type_manifest.json
represents one document type and its expected classification/extraction-rule
outcome. A failure here means our pipeline's handling of that document type's
blueprint output or its tenant configuration (required fields, confidence
floor) regressed.

See docs/documentai-api/qa-and-troubleshooting.md for how to triage a
failure, and tests/regression/document_type_manifest.json for known
coverage gaps.
"""

import json
import unittest.mock

import pytest

from documentai_api.pipeline.bda import run_bda_result_pipeline
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.response_codes import ResponseCodes

from .conftest import RegressionCase, load_regression_cases

pytestmark = pytest.mark.regression


def _get_ddb_record(metadata_table, file_name: str) -> dict:
    response = metadata_table.get_item(Key={"fileName": file_name})
    record = response.get("Item")
    assert record is not None, f"no DDB record written for {file_name}"
    return record


def _missing_required_field_list(record: dict) -> list[str]:
    """missingRequiredFieldList is persisted as a JSON-encoded string, not a native list."""
    raw = record.get(DocumentMetadata.MISSING_REQUIRED_FIELD_LIST)
    if raw is None:
        return []
    return json.loads(raw) if isinstance(raw, str) else raw


@pytest.mark.parametrize(
    "case", load_regression_cases(), ids=lambda c: f"{c.category}/{c.blueprint}"
)
def test_document_type_regression(
    case: RegressionCase, seed_bda_case, regression_report, regression_env
):
    """A canned BDA result for this document type classifies/extracts as expected."""
    bucket_name, job_metadata_key, file_name = seed_bda_case(case)

    details: dict = {}
    try:
        response = run_bda_result_pipeline(bucket_name, job_metadata_key)
        record = _get_ddb_record(regression_env["metadata_table"], file_name)

        details = {
            "response_code": record.get(DocumentMetadata.RESPONSE_CODE),
            "matched_document_class": response.get("matched_document_class"),
            "missing_required_field_list": _missing_required_field_list(record),
        }

        # The dict classify_extraction_result returns synchronously always
        # reports success/"000" - it's built before extraction rules are
        # re-evaluated for the final persisted state. The DDB record's
        # responseCode (written moments later by finalize_v1_response) is the
        # one API callers actually see, so that's the authoritative check for
        # missing-required-field regressions.
        assert response["validation_passed"] is True, response
        assert response["matched_document_class"] == case.document_class
        assert record.get(DocumentMetadata.BDA_MATCHED_DOCUMENT_CLASS) == case.document_class
        assert record.get(DocumentMetadata.RESPONSE_CODE) == case.expected_response_code
        assert sorted(_missing_required_field_list(record)) == sorted(
            case.expected_missing_required_fields
        )
    except AssertionError as e:
        regression_report(case, passed=False, details={**details, "error": str(e)})
        raise
    except Exception as e:  # noqa: BLE001 - want every unexpected error triaged, not just assertions
        regression_report(case, passed=False, details={**details, "error": repr(e)})
        raise
    else:
        regression_report(case, passed=True, details=details)


def test_no_matching_blueprint_is_reported_not_silently_dropped(seed_bda_case, regression_env):
    """A document BDA couldn't match to any blueprint surfaces as NO_CUSTOM_BLUEPRINT_MATCHED.

    Regression-guards the "unexpected blueprint result" triage path itself -
    if BDA detects real document content but nothing matches a configured
    blueprint, that must be visible (missing/renamed blueprint, bad
    description) rather than silently swallowed.
    """
    case = RegressionCase(
        category="_meta",
        blueprint="unregistered-blueprint",
        document_class="unrecognized",
        fields={},
    )
    bucket_name, job_metadata_key, file_name = seed_bda_case(case)

    # Overwrite the canned result with one that has no matched_blueprint but
    # does contain enough extractable text to be considered "a real document".
    result_key = job_metadata_key.replace("job_metadata.json", "0/result.json")
    long_text_result = {
        "matched_blueprint": {},
        "document_class": {"type": "unknown"},
        "standard_output": {"text": "a" * 200},
    }
    regression_env["bucket"].put_object(Key=result_key, Body=json.dumps(long_text_result).encode())

    # get_text_from_standard_blueprint's exact parsing of "standard_output" is
    # covered elsewhere (tests/utils/test_bda_util.py); stub it here so this
    # test stays focused on the classification/response-code regression, not
    # BDA's standard-output text format.
    with unittest.mock.patch(
        "documentai_api.processors.bda.get_text_from_standard_blueprint",
        return_value="a" * 200,
    ):
        response = run_bda_result_pipeline(bucket_name, job_metadata_key)

    record = _get_ddb_record(regression_env["metadata_table"], file_name)
    assert response["response_code"] == ResponseCodes.NO_BLUEPRINT_MATCHED
    assert not record.get(DocumentMetadata.BDA_MATCHED_BLUEPRINT_NAME)
