"""Tests for the /evaluation endpoint."""

import pytest

from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.evaluations import EvaluationKey, EvaluationStatus, NotEvaluatedReason
from documentai_api.utils.jobs import JobStatus
from documentai_api.utils.response_codes import ResponseCodes

TEST_JOB_ID = "00000000-0000-4000-8000-000000000001"
EVALUATION_URL = f"/v1/documents/{TEST_JOB_ID}/evaluation"

_PASS = EvaluationStatus.PASS
_FAIL = EvaluationStatus.FAIL
_NOT_EVALUATED = EvaluationStatus.NOT_EVALUATED

_ALL_KEYS = {
    EvaluationKey.PASSWORD_PROTECTED,
    EvaluationKey.DOCUMENT_DETECTED,
    EvaluationKey.BLUR,
    EvaluationKey.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
    EvaluationKey.MULTIPLE_DOCUMENTS_IN_MULTIPAGE,
    EvaluationKey.MISCATEGORIZATION,
    EvaluationKey.MISSING_FIELDS,
    EvaluationKey.EXTRACTION_CONFIDENCE,
}


@pytest.fixture(autouse=True)
def _disable_auth(disable_auth):
    pass


def _job(response_code, extra_ddb=None):
    ddb = {
        DocumentMetadata.TENANT_ID: "test-tenant",
        DocumentMetadata.FILE_NAME: "test.pdf",
        DocumentMetadata.RESPONSE_CODE: response_code,
        DocumentMetadata.CREATED_AT: "2024-01-01T00:00:00Z",
        **(extra_ddb or {}),
    }
    return JobStatus(
        ddb_record=ddb,
        object_key="test.pdf",
        process_status="success",
        v1_response_json='{"jobId": "test"}',
    )


# =============================================================================
# HTTP-level
# =============================================================================


def test_evaluation_not_found(api_client, mocker):
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = JobStatus(
        ddb_record=None, object_key=None, process_status=None, v1_response_json=None
    )
    assert api_client.get(EVALUATION_URL).status_code == 404


def test_evaluation_still_processing(api_client, mocker):
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = JobStatus(
        ddb_record={DocumentMetadata.TENANT_ID: "test-tenant"},
        object_key="test.pdf",
        process_status="started",
        v1_response_json=None,
    )
    assert api_client.get(EVALUATION_URL).status_code == 400


def test_evaluation_wrong_tenant(api_client, mocker):
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = JobStatus(
        ddb_record={DocumentMetadata.TENANT_ID: "other-tenant"},
        object_key="test.pdf",
        process_status="success",
        v1_response_json='{"jobId": "test"}',
    )
    assert api_client.get(EVALUATION_URL).status_code == 404


def test_evaluation_invalid_uuid(api_client):
    assert api_client.get("/v1/documents/not-a-uuid/evaluation").status_code == 422


# =============================================================================
# Response shape
# =============================================================================


def test_evaluation_response_shape(api_client, mocker):
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = _job(
        ResponseCodes.SUCCESS
    )
    data = api_client.get(EVALUATION_URL).json()
    assert data["jobId"] == TEST_JOB_ID
    assert data["responseCode"] == ResponseCodes.SUCCESS
    assert data["createdAt"] == "2024-01-01T00:00:00Z"
    assert set(data["evaluations"].keys()) == _ALL_KEYS


# =============================================================================
# Unhandled / safe-default codes — all not_evaluated
# =============================================================================


@pytest.mark.parametrize(
    ("response_code", "expected_reason"),
    [
        (ResponseCodes.PROCESSING_EXCLUDED, NotEvaluatedReason.STOPPED_PROCESSING_EXCLUDED),
        (ResponseCodes.AI_CONSENT_DECLINED, NotEvaluatedReason.STOPPED_AI_CONSENT_DECLINED),
        (
            ResponseCodes.SKIPPED_PER_PRECLASSIFICATION,
            NotEvaluatedReason.STOPPED_SKIPPED_PER_PRECLASSIFICATION,
        ),
        (ResponseCodes.INTERNAL_PROCESSING_ERROR, NotEvaluatedReason.STOPPED_INTERNAL_ERROR),
    ],
)
def test_evaluation_safe_default_codes_all_not_evaluated(
    api_client, mocker, response_code, expected_reason
):
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = _job(response_code)
    evals = api_client.get(EVALUATION_URL).json()["evaluations"]
    assert all(e["status"] == _NOT_EVALUATED for e in evals.values())
    assert all(e["reason"] == expected_reason for e in evals.values())


# =============================================================================
# Success — signals read from DDB
# =============================================================================


def test_evaluation_success_clean_document_all_pass(api_client, mocker):
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = _job(
        ResponseCodes.SUCCESS,
        extra_ddb={
            DocumentMetadata.IS_PASSWORD_PROTECTED: False,
            DocumentMetadata.IS_DOCUMENT_BLURRY: False,
            DocumentMetadata.PRECLASSIFICATION_CATEGORY_MATCH: True,
            DocumentMetadata.MISSING_REQUIRED_FIELD_LIST: [],
            DocumentMetadata.EXTRACTION_RULES_CONFIGURED: True,
            DocumentMetadata.EXTRACTION_CONFIDENCE_THRESHOLD: 0.65,
        },
    )
    evals = api_client.get(EVALUATION_URL).json()["evaluations"]
    assert all(e["status"] == _PASS for e in evals.values())


def test_evaluation_success_password_protected_signal(api_client, mocker):
    """IS_PASSWORD_PROTECTED=True on a success code still reports fail for that key."""
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = _job(
        ResponseCodes.SUCCESS,
        extra_ddb={DocumentMetadata.IS_PASSWORD_PROTECTED: True},
    )
    evals = api_client.get(EVALUATION_URL).json()["evaluations"]
    assert evals[EvaluationKey.PASSWORD_PROTECTED]["status"] == _FAIL


def test_evaluation_success_blur_detected_not_enforced(api_client, mocker):
    """blur_enabled=True, blur_enforced=False: code 000 but IS_DOCUMENT_BLURRY=True."""
    blur_reason = "Low average sharpness detected across all quadrants."
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = _job(
        ResponseCodes.SUCCESS,
        extra_ddb={
            DocumentMetadata.IS_DOCUMENT_BLURRY: True,
            DocumentMetadata.IS_DOCUMENT_BLURRY_REASON: blur_reason,
        },
    )
    evals = api_client.get(EVALUATION_URL).json()["evaluations"]
    assert evals[EvaluationKey.BLUR]["status"] == _FAIL
    assert evals[EvaluationKey.BLUR]["reason"] == blur_reason


def test_evaluation_success_blur_pass_reason_surfaced(api_client, mocker):
    """Blur skip reason (e.g. not a document) is surfaced on pass."""
    skip_reason = "Blur check was skipped — insufficient text detected to evaluate."
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = _job(
        ResponseCodes.SUCCESS,
        extra_ddb={
            DocumentMetadata.IS_DOCUMENT_BLURRY: False,
            DocumentMetadata.IS_DOCUMENT_BLURRY_REASON: skip_reason,
        },
    )
    evals = api_client.get(EVALUATION_URL).json()["evaluations"]
    assert evals[EvaluationKey.BLUR]["status"] == _PASS
    assert evals[EvaluationKey.BLUR]["reason"] == skip_reason


def test_evaluation_success_miscategorization_from_signal(api_client, mocker):
    """PRECLASSIFICATION_CATEGORY_MATCH=False reports fail even without a 102 code."""
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = _job(
        ResponseCodes.SUCCESS,
        extra_ddb={DocumentMetadata.PRECLASSIFICATION_CATEGORY_MATCH: False},
    )
    evals = api_client.get(EVALUATION_URL).json()["evaluations"]
    assert evals[EvaluationKey.MISCATEGORIZATION]["status"] == _FAIL


def test_evaluation_success_missing_fields_from_signal(api_client, mocker):
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = _job(
        ResponseCodes.SUCCESS,
        extra_ddb={
            DocumentMetadata.MISSING_REQUIRED_FIELD_LIST: ["field_a", "field_b"],
            DocumentMetadata.EXTRACTION_RULES_CONFIGURED: True,
        },
    )
    evals = api_client.get(EVALUATION_URL).json()["evaluations"]
    assert evals[EvaluationKey.MISSING_FIELDS]["status"] == _FAIL


def test_evaluation_legacy_document_missing_fields_and_confidence_not_evaluated(api_client, mocker):
    """Docs processed before enrichment lack sentinel fields — both keys report not_evaluated."""
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = _job(
        ResponseCodes.SUCCESS,
        extra_ddb={},  # no EXTRACTION_RULES_CONFIGURED, no EXTRACTION_CONFIDENCE_THRESHOLD
    )
    evals = api_client.get(EVALUATION_URL).json()["evaluations"]
    assert evals[EvaluationKey.MISSING_FIELDS]["status"] == _NOT_EVALUATED
    assert evals[EvaluationKey.MISSING_FIELDS]["reason"] == NotEvaluatedReason.LEGACY_DOCUMENT
    assert evals[EvaluationKey.EXTRACTION_CONFIDENCE]["status"] == _NOT_EVALUATED
    assert (
        evals[EvaluationKey.EXTRACTION_CONFIDENCE]["reason"] == NotEvaluatedReason.LEGACY_DOCUMENT
    )


def test_evaluation_success_extraction_confidence_from_signal(api_client, mocker):
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = _job(
        ResponseCodes.SUCCESS,
        extra_ddb={
            DocumentMetadata.BELOW_EXTRACTION_CONFIDENCE_FLOOR: True,
            DocumentMetadata.EXTRACTION_CONFIDENCE_THRESHOLD: 0.65,
        },
    )
    evals = api_client.get(EVALUATION_URL).json()["evaluations"]
    assert evals[EvaluationKey.EXTRACTION_CONFIDENCE]["status"] == _FAIL


def test_evaluation_success_document_detected_reason(api_client, mocker):
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = _job(
        ResponseCodes.SUCCESS
    )
    evals = api_client.get(EVALUATION_URL).json()["evaluations"]
    assert evals[EvaluationKey.DOCUMENT_DETECTED]["reason"] == "Sufficient text detected."


def test_evaluation_success_password_protected_pass_reason(api_client, mocker):
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = _job(
        ResponseCodes.SUCCESS,
        extra_ddb={DocumentMetadata.IS_PASSWORD_PROTECTED: False},
    )
    evals = api_client.get(EVALUATION_URL).json()["evaluations"]
    assert (
        evals[EvaluationKey.PASSWORD_PROTECTED]["reason"] == "Document is not password protected."
    )


# =============================================================================
# Stop codes — stop key is fail, tail is not_evaluated, reached keys use signals
# =============================================================================


@pytest.mark.parametrize(
    ("response_code", "stop_key", "not_evaluated_reason"),
    [
        (
            ResponseCodes.PASSWORD_PROTECTED,
            EvaluationKey.PASSWORD_PROTECTED,
            NotEvaluatedReason.STOPPED_PASSWORD_PROTECTED,
        ),
        (
            ResponseCodes.NO_DOCUMENT_DETECTED,
            EvaluationKey.DOCUMENT_DETECTED,
            NotEvaluatedReason.STOPPED_NO_DOCUMENT,
        ),
        (
            ResponseCodes.BLURRY_DOCUMENT_DETECTED,
            EvaluationKey.BLUR,
            NotEvaluatedReason.STOPPED_BLURRY,
        ),
        (
            ResponseCodes.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
            EvaluationKey.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
            NotEvaluatedReason.STOPPED_MULTIPLE_DOCUMENTS,
        ),
        (
            ResponseCodes.MULTIPLE_DOCUMENTS_IN_MULTIPAGE,
            EvaluationKey.MULTIPLE_DOCUMENTS_IN_MULTIPAGE,
            NotEvaluatedReason.STOPPED_MULTIPLE_DOCUMENTS_IN_MULTIPAGE,
        ),
    ],
)
def test_evaluation_stop_code_structure(
    api_client, mocker, response_code, stop_key, not_evaluated_reason
):
    from documentai_api.utils.evaluations import EVALUATION_PIPELINE

    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = _job(response_code)
    evals = api_client.get(EVALUATION_URL).json()["evaluations"]

    stop_index = EVALUATION_PIPELINE.index(stop_key)
    for i, key in enumerate(EVALUATION_PIPELINE):
        if i < stop_index:
            assert evals[key]["status"] == _PASS, f"{key} should be pass"
        elif i == stop_index:
            assert evals[key]["status"] == _FAIL, f"{key} should be fail"
        else:
            assert evals[key]["status"] == _NOT_EVALUATED, f"{key} should be not_evaluated"
            assert evals[key]["reason"] == not_evaluated_reason


def test_evaluation_stop_code_reached_keys_use_signals(api_client, mocker):
    """For a 400 (multiple docs) stop, blur is reached and reads its own signal."""
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = _job(
        ResponseCodes.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
        extra_ddb={
            DocumentMetadata.IS_DOCUMENT_BLURRY: True,
            DocumentMetadata.IS_DOCUMENT_BLURRY_REASON: "Low sharpness.",
        },
    )
    evals = api_client.get(EVALUATION_URL).json()["evaluations"]
    # blur is before multipleDocuments in the pipeline — it was reached
    assert evals[EvaluationKey.BLUR]["status"] == _FAIL
    assert evals[EvaluationKey.BLUR]["reason"] == "Low sharpness."
    # multipleDocumentsOnSinglePage is the stop key
    assert evals[EvaluationKey.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE]["status"] == _FAIL


# =============================================================================
# Extraction trio (101/102/105) — co-evaluated from signals, not sequential gates
# =============================================================================


def test_evaluation_extraction_trio_all_evaluated_independently(api_client, mocker):
    """101/102/105 all route through signal path — all three keys are evaluated."""
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = _job(
        ResponseCodes.MISSING_FIELDS,
        extra_ddb={
            DocumentMetadata.PRECLASSIFICATION_CATEGORY_MATCH: False,
            DocumentMetadata.MISSING_REQUIRED_FIELD_LIST: ["field_a"],
            DocumentMetadata.EXTRACTION_RULES_CONFIGURED: True,
            DocumentMetadata.BELOW_EXTRACTION_CONFIDENCE_FLOOR: True,
            DocumentMetadata.EXTRACTION_CONFIDENCE_THRESHOLD: 0.65,
        },
    )
    evals = api_client.get(EVALUATION_URL).json()["evaluations"]
    assert evals[EvaluationKey.MISCATEGORIZATION]["status"] == _FAIL
    assert evals[EvaluationKey.MISSING_FIELDS]["status"] == _FAIL
    assert evals[EvaluationKey.EXTRACTION_CONFIDENCE]["status"] == _FAIL


def test_evaluation_extraction_trio_no_not_evaluated(api_client, mocker):
    """For 101/102/105, extractionConfidence is never not_evaluated — it has a stored signal."""
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = _job(
        ResponseCodes.MISCATEGORIZED,
        extra_ddb={
            DocumentMetadata.PRECLASSIFICATION_CATEGORY_MATCH: False,
            DocumentMetadata.EXTRACTION_CONFIDENCE_THRESHOLD: 0.65,
        },
    )
    evals = api_client.get(EVALUATION_URL).json()["evaluations"]
    assert evals[EvaluationKey.EXTRACTION_CONFIDENCE]["status"] != _NOT_EVALUATED


# =============================================================================
# Blurry — stop key is fail, reason from DDB
# =============================================================================


def test_evaluation_blurry_enforced_is_fail(api_client, mocker):
    blur_reason = "Low average sharpness detected across all quadrants."
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = _job(
        ResponseCodes.BLURRY_DOCUMENT_DETECTED,
        extra_ddb={
            DocumentMetadata.IS_DOCUMENT_BLURRY: True,
            DocumentMetadata.IS_DOCUMENT_BLURRY_REASON: blur_reason,
        },
    )
    evals = api_client.get(EVALUATION_URL).json()["evaluations"]
    assert evals[EvaluationKey.BLUR]["status"] == _FAIL
    assert evals[EvaluationKey.BLUR]["reason"] == blur_reason


# =============================================================================
# NO_BLUEPRINT_MATCHED (002) — BDA ran / BDA not invoked
# =============================================================================


def test_evaluation_no_blueprint_matched_with_arn_evaluates_from_signals(api_client, mocker):
    """002 + BDA_INVOCATION_ARN present -> BDA ran, evaluate all keys from signals."""
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = _job(
        ResponseCodes.NO_BLUEPRINT_MATCHED,
        extra_ddb={
            DocumentMetadata.BDA_INVOCATION_ARN: "arn:aws:bda:us-east-1:123:job/1",
            DocumentMetadata.EXTRACTION_RULES_CONFIGURED: True,
            DocumentMetadata.EXTRACTION_CONFIDENCE_THRESHOLD: 0.65,
        },
    )
    evals = api_client.get(EVALUATION_URL).json()["evaluations"]
    assert set(evals.keys()) == _ALL_KEYS
    assert all(e["status"] != _NOT_EVALUATED for e in evals.values())


def test_evaluation_no_blueprint_matched_without_arn_all_not_evaluated(api_client, mocker):
    """002 + no BDA_INVOCATION_ARN -> BDA never ran -> all not_evaluated."""
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = _job(
        ResponseCodes.NO_BLUEPRINT_MATCHED,
    )
    evals = api_client.get(EVALUATION_URL).json()["evaluations"]
    assert all(e["status"] == _NOT_EVALUATED for e in evals.values())


# =============================================================================
# Unknown code safe default
# =============================================================================


def test_evaluation_unknown_code_defaults_to_not_evaluated(api_client, mocker):
    """Unrecognized response code falls to not_evaluated rather than silently passing."""
    mocker.patch("documentai_api.app_evaluation.get_job_status").return_value = _job("999")
    evals = api_client.get(EVALUATION_URL).json()["evaluations"]
    assert all(e["status"] == _NOT_EVALUATED for e in evals.values())
