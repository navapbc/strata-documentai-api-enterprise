from datetime import UTC, datetime

import pytest

from documentai_api.config.constants import BdaResponseFields, ProcessStatus
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils import response_builder as response_builder_util
from documentai_api.utils.dto import ClassificationData, InternalApiResponse
from documentai_api.utils.response_codes import ResponseCodes


@pytest.mark.parametrize(
    ("response_code", "matched_document_class"),
    [
        (ResponseCodes.SUCCESS, "income"),
        (ResponseCodes.NO_DOCUMENT_DETECTED, "income"),
        (ResponseCodes.SUCCESS, None),
    ],
)
def test_get_internal_api_response(response_code, matched_document_class, ddb_doc_metadata_table):
    ddb_record = {
        DocumentMetadata.FILE_NAME: "test-key",
        DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY: "income",
    }
    ddb_doc_metadata_table.put_item(Item=ddb_record)

    response = response_builder_util.get_internal_api_response(
        "test-key", response_code, matched_document_class
    )

    assert response == InternalApiResponse(
        validation_passed=ResponseCodes.is_success_response_code(response_code),
        document_category="income",
        matched_document_class=matched_document_class,
        response_code=response_code,
        response_message=ResponseCodes.get_message(response_code),
    )


@pytest.mark.parametrize(
    (
        "job_status",
        "error_message",
        "additional_info",
        "include_extracted_data",
        "expected_status",
        "expected_message",
        "expected_error",
        "expected_response_code",
    ),
    [
        (
            ProcessStatus.SUCCESS.value,
            None,
            None,
            False,
            "completed",
            "Document processed successfully",
            None,
            ResponseCodes.SUCCESS,
        ),
        (
            ProcessStatus.SUCCESS.value,
            None,
            None,
            True,
            "completed",
            "Document processed successfully",
            None,
            ResponseCodes.SUCCESS,
        ),
        (
            ProcessStatus.NO_CUSTOM_BLUEPRINT_MATCHED.value,
            None,
            None,
            False,
            "completed",
            "Document processed but no matching template found",
            None,
            ResponseCodes.DOCUMENT_TYPE_NOT_IMPLEMENTED,
        ),
        (
            ProcessStatus.FAILED.value,
            "Test error",
            "Additional context",
            False,
            "failed",
            None,
            "Test error",
            ResponseCodes.INTERNAL_PROCESSING_ERROR,
        ),
        (
            ProcessStatus.NO_DOCUMENT_DETECTED.value,
            None,
            "No content",
            False,
            "not_supported",
            "Unable to extract meaningful document content",
            None,
            ResponseCodes.NO_DOCUMENT_DETECTED,
        ),
        (
            ProcessStatus.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE.value,
            None,
            "Unsupported type",
            False,
            "not_supported",
            "Document type not supported",
            None,
            ResponseCodes.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
        ),
        (
            ProcessStatus.PASSWORD_PROTECTED.value,
            None,
            "Unsupported type",
            False,
            "not_supported",
            "Document type not supported",
            None,
            ResponseCodes.PASSWORD_PROTECTED,
        ),
        (
            ProcessStatus.STARTED.value,
            None,
            None,
            False,
            "processing",
            "Document processing in progress",
            None,
            None,
        ),
    ],
)
def test_build_v1_api_response(
    job_status: str,
    error_message: str | None,
    additional_info: str | None,
    include_extracted_data: bool,
    expected_status: str | None,
    expected_message: str | None,
    expected_error: str | None,
    expected_response_code: str | None,
    s3_bucket,
    ddb_doc_metadata_table,
    mocker,
):
    import json

    year = datetime.now().year
    created_at = datetime(year, 1, 1, 12, 0, 0, tzinfo=UTC)
    bda_completed_at = datetime(year, 1, 1, 12, 0, 10, tzinfo=UTC)
    matched_document_class = "paystub"
    data = ClassificationData(
        matched_document_class=matched_document_class, additional_info=additional_info
    )

    bda_results = {
        BdaResponseFields.EXPLAINABILITY_INFO: [
            {
                "field_name_1": {"confidence": 0.95, "value": "value1"},
                "field_name_2": {"confidence": 0.85, "value": "value2"},
            }
        ]
    }
    bda_results_object = s3_bucket.put_object(Key="key.json", Body=json.dumps(bda_results))

    ddb_record = {
        DocumentMetadata.FILE_NAME: "test-key",
        DocumentMetadata.JOB_ID: "test-job-id",
        DocumentMetadata.BDA_OUTPUT_S3_URI: f"s3://{bda_results_object.bucket_name}/{bda_results_object.key}",
        DocumentMetadata.BDA_MATCHED_DOCUMENT_CLASS: "paystub",
        DocumentMetadata.TOTAL_PROCESSING_TIME_SECONDS: 10,
        DocumentMetadata.BDA_COMPLETED_AT: bda_completed_at.isoformat(),
        DocumentMetadata.CREATED_AT: created_at.isoformat(),
        DocumentMetadata.FIELD_CONFIDENCE_SCORES: '[{"field_name_1": 0.95}, {"field_name_2": 0.85}]',
    }
    ddb_doc_metadata_table.put_item(Item=ddb_record)

    # build_v1_api_response stores the flat, verbatim canonical form; camelCase +
    # nesting is applied later at the presentation boundary (present_v1_response).
    expected_fields_value = {
        "field_name_1": {
            "confidence": 0.95,
            "value": "value1" if include_extracted_data else "<redacted>",
            "displayName": "Field Name 1",
        },
        "field_name_2": {
            "confidence": 0.85,
            "value": "value2" if include_extracted_data else "<redacted>",
            "displayName": "Field Name 2",
        },
    }

    response = response_builder_util.build_v1_api_response(
        "test-key", job_status, data, error_message, include_extracted_data
    )

    expected_response = {
        "jobId": "test-job-id",
        "jobStatus": expected_status,
        "createdAt": created_at.isoformat(),
        "completedAt": bda_completed_at.isoformat(),
        "totalProcessingTimeSeconds": 10.0,
        "matchedDocumentClass": matched_document_class,
    }

    if expected_message:
        expected_response["message"] = expected_message

    if expected_error:
        expected_response["error"] = expected_error

    if additional_info:
        expected_response["additionalInfo"] = additional_info

    if job_status == ProcessStatus.SUCCESS.value:
        expected_response["fields"] = expected_fields_value
    elif ProcessStatus.is_successful(job_status):
        expected_response["fields"] = {}

    if expected_response_code:
        expected_response["responseCode"] = expected_response_code
        expected_response["responseMessage"] = ResponseCodes.get_message(expected_response_code)

    assert response == expected_response


def test_build_v1_api_response_no_record(
    ddb_doc_metadata_table,
):
    with pytest.raises(ValueError, match="DDB record not found for file: test-does-not-exist"):
        response_builder_util.build_v1_api_response(
            "test-does-not-exist",
            ProcessStatus.SUCCESS,
            data=None,
            error_message=None,
            include_extracted_data=False,
        )


def test_build_v1_api_response_empty_record(
    ddb_doc_metadata_table,
):
    # Not really possible to have a truly empty dictionary returned, it needs to
    # at least have the primary key to be able to find at all/no error with "not
    # found"

    ddb_record = {
        DocumentMetadata.FILE_NAME: "test-key",
    }
    ddb_doc_metadata_table.put_item(Item=ddb_record)

    response = response_builder_util.build_v1_api_response(
        "test-key",
        ProcessStatus.SUCCESS,
        data=None,
        error_message=None,
        include_extracted_data=False,
    )

    assert response == {
        "fields": dict(),
        "message": "Document processed successfully",
        "jobStatus": "completed",
        "responseCode": ResponseCodes.SUCCESS,
        "responseMessage": ResponseCodes.get_message(ResponseCodes.SUCCESS),
    }


def test_build_v1_api_response_with_bounding_box(
    s3_bucket,
    ddb_doc_metadata_table,
    bda_result_with_geometry,
):
    """include_bounding_box=True includes geometry and fieldType in fields."""
    import json

    bda_obj = s3_bucket.put_object(Key="bbox-test.json", Body=json.dumps(bda_result_with_geometry))

    ddb_record = {
        DocumentMetadata.FILE_NAME: "bbox-test-key",
        DocumentMetadata.JOB_ID: "bbox-job-id",
        DocumentMetadata.BDA_OUTPUT_S3_URI: f"s3://{bda_obj.bucket_name}/{bda_obj.key}",
        DocumentMetadata.BDA_MATCHED_DOCUMENT_CLASS: "Lease",
        DocumentMetadata.CREATED_AT: "2025-01-01T00:00:00+00:00",
        DocumentMetadata.FIELD_CONFIDENCE_SCORES: '[{"tenant_name": 0.93}, {"amount": 0.88}]',
    }
    ddb_doc_metadata_table.put_item(Item=ddb_record)

    response = response_builder_util.build_v1_api_response(
        "bbox-test-key",
        ProcessStatus.SUCCESS.value,
        include_extracted_data=True,
        include_bounding_box=True,
    )

    # fields are stored flat/verbatim; geometry + fieldType present on field with geometry
    assert "geometry" in response["fields"]["tenant_name"]
    assert response["fields"]["tenant_name"]["fieldType"] == "string"
    assert response["fields"]["tenant_name"]["geometry"][0]["boundingBox"]["top"] == 0.31

    # field without geometry in BDA output has no geometry key
    assert "geometry" not in response["fields"]["amount"]
    assert "fieldType" not in response["fields"]["amount"]


def test_build_v1_api_response_without_bounding_box_no_leakage(
    s3_bucket,
    ddb_doc_metadata_table,
    bda_result_with_geometry,
):
    """include_bounding_box=False does not leak geometry into fields."""
    import json

    bda_obj = s3_bucket.put_object(Key="no-bbox.json", Body=json.dumps(bda_result_with_geometry))

    ddb_record = {
        DocumentMetadata.FILE_NAME: "no-bbox-key",
        DocumentMetadata.JOB_ID: "no-bbox-job-id",
        DocumentMetadata.BDA_OUTPUT_S3_URI: f"s3://{bda_obj.bucket_name}/{bda_obj.key}",
        DocumentMetadata.BDA_MATCHED_DOCUMENT_CLASS: "Lease",
        DocumentMetadata.CREATED_AT: "2025-01-01T00:00:00+00:00",
        DocumentMetadata.FIELD_CONFIDENCE_SCORES: '[{"tenant_name": 0.93}]',
    }
    ddb_doc_metadata_table.put_item(Item=ddb_record)

    response = response_builder_util.build_v1_api_response(
        "no-bbox-key",
        ProcessStatus.SUCCESS.value,
        include_extracted_data=True,
        include_bounding_box=False,
    )

    assert "geometry" not in response["fields"]["tenant_name"]
    assert "fieldType" not in response["fields"]["tenant_name"]


def test_build_v1_api_response_applies_extraction_rules(
    s3_bucket,
    ddb_doc_metadata_table,
    extraction_rules_table,
    mocker,
):
    import json

    year = datetime.now().year
    created_at = datetime(year, 1, 1, 12, 0, 0, tzinfo=UTC)
    bda_completed_at = datetime(year, 1, 1, 12, 0, 10, tzinfo=UTC)

    bda_results = {
        BdaResponseFields.EXPLAINABILITY_INFO: [
            {
                "ssn": {"confidence": 0.95, "value": "123-45-6789"},
                "wages": {"confidence": 0.9, "value": "50000"},
                "extra_field": {"confidence": 0.8, "value": "ignored"},
            }
        ]
    }
    bda_results_object = s3_bucket.put_object(Key="key.json", Body=json.dumps(bda_results))

    ddb_record = {
        DocumentMetadata.FILE_NAME: "test-key",
        DocumentMetadata.JOB_ID: "test-job-id",
        DocumentMetadata.BDA_OUTPUT_S3_URI: f"s3://{bda_results_object.bucket_name}/{bda_results_object.key}",
        DocumentMetadata.BDA_MATCHED_DOCUMENT_CLASS: "W2",
        DocumentMetadata.TOTAL_PROCESSING_TIME_SECONDS: 10,
        DocumentMetadata.BDA_COMPLETED_AT: bda_completed_at.isoformat(),
        DocumentMetadata.CREATED_AT: created_at.isoformat(),
        DocumentMetadata.FIELD_CONFIDENCE_SCORES: '[{"ssn": 0.95}, {"wages": 0.9}, {"extra_field": 0.8}]',
        "tenantId": "t1",
    }
    ddb_doc_metadata_table.put_item(Item=ddb_record)

    extraction_rules_table.put_item(
        Item={
            "tenantId": "t1",
            "documentType": "W2",
            "requiredFields": ["ssn", "wages", "federal_tax"],
            "optionalFields": [],
            "createdAt": "2026-01-01",
            "updatedAt": "2026-01-01",
        }
    )

    response = response_builder_util.build_v1_api_response("test-key", ProcessStatus.SUCCESS.value)

    # extra_field filtered out, federal_tax missing
    assert "extraField" not in response["fields"]
    assert "ssn" in response["fields"] or "Ssn" in response["fields"]
    assert response["missingRequiredFieldList"] == ["federal_tax"]
    assert response["responseCode"] == ResponseCodes.MISSING_FIELDS


def test_build_v1_api_response_extraction_rules_match_nested_fields(
    s3_bucket,
    ddb_doc_metadata_table,
    extraction_rules_table,
    mocker,
):
    """Extraction rules match on verbatim dotted names; kept fields nest in the response."""
    import json

    year = datetime.now().year
    created_at = datetime(year, 1, 1, 12, 0, 0, tzinfo=UTC)
    bda_completed_at = datetime(year, 1, 1, 12, 0, 10, tzinfo=UTC)

    bda_results = {
        BdaResponseFields.EXPLAINABILITY_INFO: [
            {
                "applicant": {
                    "first_name": {"confidence": 0.95, "value": "Ada"},
                    "last_name": {"confidence": 0.9, "value": "Lovelace"},
                },
                "extra_field": {"confidence": 0.8, "value": "ignored"},
            }
        ]
    }
    bda_results_object = s3_bucket.put_object(Key="key.json", Body=json.dumps(bda_results))

    ddb_record = {
        DocumentMetadata.FILE_NAME: "test-key",
        DocumentMetadata.JOB_ID: "test-job-id",
        DocumentMetadata.BDA_OUTPUT_S3_URI: f"s3://{bda_results_object.bucket_name}/{bda_results_object.key}",
        DocumentMetadata.BDA_MATCHED_DOCUMENT_CLASS: "W2",
        DocumentMetadata.TOTAL_PROCESSING_TIME_SECONDS: 10,
        DocumentMetadata.BDA_COMPLETED_AT: bda_completed_at.isoformat(),
        DocumentMetadata.CREATED_AT: created_at.isoformat(),
        DocumentMetadata.FIELD_CONFIDENCE_SCORES: (
            '[{"applicant.first_name": 0.95}, {"applicant.last_name": 0.9}, {"extra_field": 0.8}]'
        ),
        "tenantId": "t1",
    }
    ddb_doc_metadata_table.put_item(Item=ddb_record)

    extraction_rules_table.put_item(
        Item={
            "tenantId": "t1",
            "documentType": "W2",
            "requiredFields": ["applicant.first_name", "applicant.middle_name"],
            "optionalFields": ["applicant.last_name"],
            "createdAt": "2026-01-01",
            "updatedAt": "2026-01-01",
        }
    )

    response = response_builder_util.build_v1_api_response(
        "test-key", ProcessStatus.SUCCESS.value, include_extracted_data=True
    )

    # Stored form is flat + verbatim: extra_field filtered out (not in rules), the
    # required/optional fields kept under their dotted blueprint names.
    assert "extra_field" not in response["fields"]
    assert response["fields"]["applicant.first_name"]["value"] == "Ada"
    assert response["fields"]["applicant.last_name"]["value"] == "Lovelace"
    # only the genuinely absent required field is reported missing (verbatim name)
    assert response["missingRequiredFieldList"] == ["applicant.middle_name"]
    assert response["responseCode"] == ResponseCodes.MISSING_FIELDS

    # The presentation boundary nests for the client, preserving verbatim names.
    presented = response_builder_util.present_v1_response(response)
    assert presented["fields"]["applicant"]["first_name"]["value"] == "Ada"
    assert presented["fields"]["applicant"]["last_name"]["value"] == "Lovelace"
    # non-fields keys pass through untouched
    assert presented["missingRequiredFieldList"] == ["applicant.middle_name"]


def test_nest_fields_shapes_and_is_idempotent():
    """nest_fields splits dotted names into nesting verbatim and no-ops when nested."""
    flat = {
        "amount": {"confidence": 0.9, "value": "1"},
        "payment_details.base_rent": {"confidence": 0.91, "value": "1200"},
        "payment_details.fees": {"confidence": 0.9, "value": ""},
    }

    nested = response_builder_util.nest_fields(flat)

    assert nested["amount"] == {"confidence": 0.9, "value": "1"}
    # segments are preserved verbatim (no case conversion)
    assert nested["payment_details"]["base_rent"]["value"] == "1200"
    assert nested["payment_details"]["fees"]["value"] == ""

    # already-nested input (e.g. a record from an earlier version) passes through unchanged
    assert response_builder_util.nest_fields(nested) == nested


def test_present_v1_response_without_fields_passes_through():
    """Responses without a fields block (errors, in-progress) are returned unchanged."""
    resp = {"jobId": "j1", "jobStatus": "failed", "error": "boom"}
    assert response_builder_util.present_v1_response(resp) == resp


def test_nest_fields_preserves_legacy_camelcase_keys():
    """Old camelCase-dotted records nest without casing being mangled."""
    legacy = {
        "tenantName": {"confidence": 0.93, "value": "Jane"},
        "paymentDetails.baseRent": {"confidence": 0.91, "value": "1200"},
    }

    nested = response_builder_util.nest_fields(legacy)

    # camelCase segments are preserved verbatim (not lowercased) and still nest
    assert nested["tenantName"] == {"confidence": 0.93, "value": "Jane"}
    assert nested["paymentDetails"]["baseRent"]["value"] == "1200"
