from datetime import UTC, datetime

import pytest

from documentai_api.config.constants import BdaResponseFields, ProcessStatus
from documentai_api.dtos.classification import ClassificationData
from documentai_api.dtos.processing import InternalApiResponse
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils import response_builder as response_builder_util
from documentai_api.utils.response_codes import ResponseCodes


@pytest.fixture(autouse=True)
def _pin_output_location(mocker):
    # get_bda_result_json validates that the result URI bucket matches
    # documentai_output_location to prevent SSRF. pin config
    # to test-bucket so tests that call through to S3 pass the check.
    mocker.patch(
        "documentai_api.services.bda.get_aws_config"
    ).return_value.documentai_output_location = "s3://test-bucket/output"


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
            "No matching blueprint found",
            None,
            ResponseCodes.NO_BLUEPRINT_MATCHED,
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
            "completed",
            "Unable to extract meaningful document content",
            None,
            ResponseCodes.NO_DOCUMENT_DETECTED,
        ),
        (
            ProcessStatus.BLURRY_DOCUMENT_DETECTED.value,
            None,
            None,
            False,
            "completed",
            "Document is blurry",
            None,
            ResponseCodes.BLURRY_DOCUMENT_DETECTED,
        ),
        (
            ProcessStatus.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE.value,
            None,
            "Unsupported type",
            False,
            "completed",
            "Document type not supported",
            None,
            ResponseCodes.MULTIPLE_DOCUMENTS_ON_SINGLE_PAGE,
        ),
        (
            ProcessStatus.MULTIPLE_DOCUMENTS_IN_MULTIPAGE.value,
            None,
            None,
            False,
            "completed",
            "Document type not supported",
            None,
            ResponseCodes.MULTIPLE_DOCUMENTS_IN_MULTIPAGE,
        ),
        (
            ProcessStatus.PASSWORD_PROTECTED.value,
            None,
            "Unsupported type",
            False,
            "completed",
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
        (
            ProcessStatus.PROCESSING_EXCLUDED.value,
            None,
            None,
            False,
            "completed",
            "Document not chosen for extraction",
            None,
            ResponseCodes.PROCESSING_EXCLUDED,
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


def test_build_v1_api_response_no_custom_blueprint_matched_but_miscategorized(
    ddb_doc_metadata_table,
):
    """A preclassification category mismatch should surface as 102  when no blueprint match."""
    year = datetime.now().year
    created_at = datetime(year, 1, 1, 12, 0, 0, tzinfo=UTC)

    ddb_record = {
        DocumentMetadata.FILE_NAME: "test-key",
        DocumentMetadata.JOB_ID: "test-job-id",
        DocumentMetadata.CREATED_AT: created_at.isoformat(),
        DocumentMetadata.PRECLASSIFICATION_CATEGORY_MATCH: False,
    }
    ddb_doc_metadata_table.put_item(Item=ddb_record)

    response = response_builder_util.build_v1_api_response(
        "test-key",
        ProcessStatus.NO_CUSTOM_BLUEPRINT_MATCHED.value,
        data=None,
        error_message=None,
        include_extracted_data=False,
    )

    assert response["responseCode"] == ResponseCodes.MISCATEGORIZED
    assert response["responseMessage"] == ResponseCodes.get_message(ResponseCodes.MISCATEGORIZED)
    # message/jobStatus stay as the terminal default - only the response code changes
    assert response["message"] == "No matching blueprint found"
    assert response["jobStatus"] == "completed"


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


def test_build_v1_api_response_missing_geometry_and_empty_fields_trigger_101(
    s3_bucket,
    ddb_doc_metadata_table,
    extraction_rules_table,
    monkeypatch,
):
    """DDB missing-geometry + empty lists union into missing_fields -> 101."""
    import json

    from documentai_api.config.constants import BdaResponseFields

    bda_results = {
        BdaResponseFields.EXPLAINABILITY_INFO: [
            {
                "GrossPay": {"confidence": 0.95, "value": "5000"},
                "PayPeriodStartDate": {"confidence": 0.12, "value": "2025-01-01"},
                "YTDGrossPay": {"confidence": 0.94, "value": ""},
            }
        ]
    }
    bda_obj = s3_bucket.put_object(Key="missing-geo.json", Body=json.dumps(bda_results))

    ddb_record = {
        DocumentMetadata.FILE_NAME: "missing-geo-key",
        DocumentMetadata.JOB_ID: "missing-geo-job",
        DocumentMetadata.BDA_OUTPUT_S3_URI: f"s3://{bda_obj.bucket_name}/{bda_obj.key}",
        DocumentMetadata.BDA_MATCHED_DOCUMENT_CLASS: "Payslip",
        DocumentMetadata.CREATED_AT: "2026-01-01T00:00:00+00:00",
        DocumentMetadata.FIELD_CONFIDENCE_SCORES: (
            '[{"GrossPay": 0.95}, {"PayPeriodStartDate": 0.12}, {"YTDGrossPay": 0.94}]'
        ),
        DocumentMetadata.BDA_MATCHED_BLUEPRINT_FIELD_MISSING_GEOMETRY_LIST: json.dumps(
            ["PayPeriodStartDate"]
        ),
        DocumentMetadata.BDA_MATCHED_BLUEPRINT_FIELD_EMPTY_LIST: json.dumps(["YTDGrossPay"]),
        "tenantId": "t1",
    }
    ddb_doc_metadata_table.put_item(Item=ddb_record)

    extraction_rules_table.put_item(
        Item={
            "tenantId": "t1",
            "documentType": "Payslip",
            "requiredFields": ["GrossPay", "PayPeriodStartDate", "YTDGrossPay"],
            "optionalFields": [],
            "createdAt": "2026-01-01",
            "updatedAt": "2026-01-01",
        }
    )

    monkeypatch.setattr(
        "documentai_api.utils.ssm.is_missing_geo_included_with_missing_fields",
        lambda: True,
    )

    response = response_builder_util.build_v1_api_response(
        "missing-geo-key", ProcessStatus.SUCCESS.value, include_extracted_data=True
    )

    assert response["responseCode"] == ResponseCodes.MISSING_FIELDS
    assert sorted(response["missingRequiredFieldList"]) == ["PayPeriodStartDate", "YTDGrossPay"]
    assert "GrossPay" in response["fields"]


# =============================================================================
# Response code precedence: 101 > 102 > 105 > 100
# =============================================================================


@pytest.mark.parametrize(
    ("below_floor", "category_match", "expected_code"),
    [
        (False, True, ResponseCodes.SUCCESS),
        (False, None, ResponseCodes.SUCCESS),
        (True, True, ResponseCodes.LOW_EXTRACTION_CONFIDENCE),
        (False, False, ResponseCodes.MISCATEGORIZED),
        (True, False, ResponseCodes.MISCATEGORIZED),  # 102 beats 105
    ],
)
def test_build_v1_api_response_success_response_code_precedence(
    s3_bucket, ddb_doc_metadata_table, below_floor, category_match, expected_code
):
    """_resolve_response_code precedence: 102 beats 105, both lose to 101."""
    import json

    bda_results = {
        BdaResponseFields.EXPLAINABILITY_INFO: [{"wages": {"confidence": 0.9, "value": "50000"}}]
    }
    bda_obj = s3_bucket.put_object(Key="prec-test.json", Body=json.dumps(bda_results))

    ddb_record = {
        DocumentMetadata.FILE_NAME: "test-file-name",
        DocumentMetadata.JOB_ID: "test-job-id",
        DocumentMetadata.BDA_OUTPUT_S3_URI: f"s3://{bda_obj.bucket_name}/{bda_obj.key}",
        DocumentMetadata.BDA_MATCHED_DOCUMENT_CLASS: "paystub",
        DocumentMetadata.CREATED_AT: "2026-01-01T00:00:00+00:00",
        DocumentMetadata.FIELD_CONFIDENCE_SCORES: '[{"wages": 0.9}]',
        DocumentMetadata.BELOW_EXTRACTION_CONFIDENCE_FLOOR: below_floor,
    }
    if category_match is not None:
        ddb_record[DocumentMetadata.PRECLASSIFICATION_CATEGORY_MATCH] = category_match
    ddb_doc_metadata_table.put_item(Item=ddb_record)

    response = response_builder_util.build_v1_api_response(
        "test-file-name", ProcessStatus.SUCCESS.value
    )

    assert response["responseCode"] == expected_code
    assert (
        response["belowExtractionConfidenceFloor"] is True
        if below_floor
        else "belowExtractionConfidenceFloor" not in response
    )


def test_build_v1_api_response_101_beats_102_and_105(
    s3_bucket, ddb_doc_metadata_table, extraction_rules_table
):
    """101 (missing required fields) takes priority over both 102 and 105."""
    import json

    bda_results = {
        BdaResponseFields.EXPLAINABILITY_INFO: [{"wages": {"confidence": 0.9, "value": "50000"}}]
    }
    bda_obj = s3_bucket.put_object(Key="prec-101.json", Body=json.dumps(bda_results))

    ddb_record = {
        DocumentMetadata.FILE_NAME: "test-file-name",
        DocumentMetadata.JOB_ID: "test-job-id",
        DocumentMetadata.BDA_OUTPUT_S3_URI: f"s3://{bda_obj.bucket_name}/{bda_obj.key}",
        DocumentMetadata.BDA_MATCHED_DOCUMENT_CLASS: "paystub",
        DocumentMetadata.CREATED_AT: "2026-01-01T00:00:00+00:00",
        DocumentMetadata.FIELD_CONFIDENCE_SCORES: '[{"wages": 0.9}]',
        DocumentMetadata.BELOW_EXTRACTION_CONFIDENCE_FLOOR: True,
        DocumentMetadata.PRECLASSIFICATION_CATEGORY_MATCH: False,
        "tenantId": "t1",
    }
    ddb_doc_metadata_table.put_item(Item=ddb_record)

    extraction_rules_table.put_item(
        Item={
            "tenantId": "t1",
            "documentType": "paystub",
            "requiredFields": ["missing_field"],
            "optionalFields": [],
            "createdAt": "2026-01-01",
            "updatedAt": "2026-01-01",
        }
    )

    response = response_builder_util.build_v1_api_response(
        "test-file-name", ProcessStatus.SUCCESS.value
    )

    assert response["responseCode"] == ResponseCodes.MISSING_FIELDS
    assert response["belowExtractionConfidenceFloor"] is True
    assert "missing_field" in response["missingRequiredFieldList"]


# =============================================================================
# userProvidedDocumentCategory echo + inferredDocumentType on 102
# =============================================================================


def _minimal_success_record(s3_bucket: object, file_name: str) -> dict:
    """Put a minimal BDA result in S3 and return a DDB record dict ready for put_item."""
    import json

    bda_results = {
        BdaResponseFields.EXPLAINABILITY_INFO: [{"wages": {"confidence": 0.9, "value": "50000"}}]
    }
    bda_obj = s3_bucket.put_object(Key=f"{file_name}.json", Body=json.dumps(bda_results))  # type: ignore[union-attr]
    return {
        DocumentMetadata.FILE_NAME: file_name,
        DocumentMetadata.JOB_ID: f"{file_name}-job",
        DocumentMetadata.BDA_OUTPUT_S3_URI: f"s3://{bda_obj.bucket_name}/{bda_obj.key}",
        DocumentMetadata.BDA_MATCHED_DOCUMENT_CLASS: "paystub",
        DocumentMetadata.CREATED_AT: "2026-01-01T00:00:00+00:00",
        DocumentMetadata.FIELD_CONFIDENCE_SCORES: '[{"wages": 0.9}]',
    }


def test_user_category_echoed_when_present(s3_bucket, ddb_doc_metadata_table):
    """UserProvidedDocumentCategory appears in the response when set on the DDB record."""
    record = _minimal_success_record(s3_bucket, "user-cat")
    record[DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY] = "income"
    ddb_doc_metadata_table.put_item(Item=record)

    response = response_builder_util.build_v1_api_response("user-cat", ProcessStatus.SUCCESS.value)

    assert response["userProvidedDocumentCategory"] == "income"


def test_user_category_absent_when_not_set(s3_bucket, ddb_doc_metadata_table):
    """UserProvidedDocumentCategory is omitted when not present on the DDB record."""
    ddb_doc_metadata_table.put_item(Item=_minimal_success_record(s3_bucket, "no-user-cat"))

    response = response_builder_util.build_v1_api_response(
        "no-user-cat", ProcessStatus.SUCCESS.value
    )

    assert "userProvidedDocumentCategory" not in response


def test_102_includes_inferred_document_type(s3_bucket, ddb_doc_metadata_table):
    """On a 102 response, inferredDocumentType is populated from preclassificationCategory."""
    record = _minimal_success_record(s3_bucket, "102-suggested")
    record[DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY] = "income"
    record[DocumentMetadata.PRECLASSIFICATION_CATEGORY_MATCH] = False
    record[DocumentMetadata.PRECLASSIFICATION_CATEGORY] = "pay stub"
    ddb_doc_metadata_table.put_item(Item=record)

    response = response_builder_util.build_v1_api_response(
        "102-suggested", ProcessStatus.SUCCESS.value
    )

    assert response["responseCode"] == ResponseCodes.MISCATEGORIZED
    assert response["userProvidedDocumentCategory"] == "income"
    assert response["inferredDocumentType"] == "pay stub"


def test_inferred_document_type_present_on_non_102(s3_bucket, ddb_doc_metadata_table):
    """InferredDocumentType is surfaced on any success response, not just 102."""
    record = _minimal_success_record(s3_bucket, "100-detected")
    record[DocumentMetadata.PRECLASSIFICATION_CATEGORY] = "pay stub"
    ddb_doc_metadata_table.put_item(Item=record)

    response = response_builder_util.build_v1_api_response(
        "100-detected", ProcessStatus.SUCCESS.value
    )

    assert response["responseCode"] == ResponseCodes.SUCCESS
    assert response["inferredDocumentType"] == "pay stub"


def test_inferred_document_type_absent_from_dict_when_not_preclassified(
    s3_bucket, ddb_doc_metadata_table
):
    """With no preclassification category, inferredDocumentType is absent from the response dict.

    None values are stripped by build_v1_api_response.
    """
    ddb_doc_metadata_table.put_item(Item=_minimal_success_record(s3_bucket, "100-no-detect"))

    response = response_builder_util.build_v1_api_response(
        "100-no-detect", ProcessStatus.SUCCESS.value
    )

    assert response["responseCode"] == ResponseCodes.SUCCESS
    assert "inferredDocumentType" not in response
