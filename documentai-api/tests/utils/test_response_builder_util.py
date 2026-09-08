import pytest

from documentai_api.dtos.processing import InternalApiResponse
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils import response_builder as response_builder_util
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
    ddb_doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: "test-key",
            DocumentMetadata.USER_PROVIDED_DOCUMENT_CATEGORY: "income",
        }
    )

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


def test_nest_fields_shapes_and_is_idempotent():
    flat = {
        "amount": {"confidence": 0.9, "value": "1"},
        "payment_details.base_rent": {"confidence": 0.91, "value": "1200"},
        "payment_details.fees": {"confidence": 0.9, "value": ""},
    }

    nested = response_builder_util.nest_fields(flat)

    assert nested["amount"] == {"confidence": 0.9, "value": "1"}
    assert nested["payment_details"]["base_rent"]["value"] == "1200"
    assert nested["payment_details"]["fees"]["value"] == ""
    assert response_builder_util.nest_fields(nested) == nested


def test_present_v1_response_without_fields_passes_through():
    resp = {"jobId": "j1", "jobStatus": "failed", "error": "boom"}
    assert response_builder_util.present_v1_response(resp) == resp


def test_nest_fields_preserves_legacy_camelcase_keys():
    legacy = {
        "tenantName": {"confidence": 0.93, "value": "Jane"},
        "paymentDetails.baseRent": {"confidence": 0.91, "value": "1200"},
    }

    nested = response_builder_util.nest_fields(legacy)

    assert nested["tenantName"] == {"confidence": 0.93, "value": "Jane"}
    assert nested["paymentDetails"]["baseRent"]["value"] == "1200"
