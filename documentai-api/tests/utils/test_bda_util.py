import pytest

from documentai_api.config.constants import ProcessStatus
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils import bda as bda_util

BDA_INVOCATION_UUID = "de8464af-d53e-44dc-a9f7-ad5360530210"
BDA_OUTPUT_BUCKET = "output-bucket"
BDA_OUTPUT_KEY = (
    f"processed/input/test-tenant/doc.pdf/{BDA_INVOCATION_UUID}/0/custom_output/job_metadata.json"
)
BDA_DDB_FILE_NAME = "input/test-tenant/doc.pdf"


@pytest.mark.parametrize(
    ("arn", "expected_region"),
    [
        ("arn:aws:bedrock-data-automation:us-east-1:123456789012:job/abc123", "us-east-1"),
        ("arn:aws:bedrock-data-automation:eu-west-1:123456789012:job/xyz789", "eu-west-1"),
        ("invalid-arn", None),
    ],
)
def test_extract_region_from_bda_arn(arn, expected_region):
    assert bda_util.extract_region_from_bda_arn(arn) == expected_region


def test_get_text_from_standard_blueprint_document_modality():
    bda_result = {
        "metadata": {"semantic_modality": "DOCUMENT"},
        "pages": [{"representation": {"text": "  Sample document text  "}}],
    }
    assert bda_util.get_text_from_standard_blueprint(bda_result) == "Sample document text"


def test_get_text_from_standard_blueprint_image_modality():
    bda_result = {
        "metadata": {"semantic_modality": "IMAGE"},
        "image": {
            "text_words": [
                {"text": "Hello"},
                {"text": "World"},
                {"text": ""},
            ]
        },
    }
    assert bda_util.get_text_from_standard_blueprint(bda_result) == "Hello World"


# =============================================================================
# get_ddb_key_from_bda_output / get_ddb_record_from_bda_output
# =============================================================================


def test_get_ddb_key_from_bda_output_returns_file_name(ddb_doc_metadata_table):
    """Realistic key with seeded record returns the correct file_name."""
    ddb_doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: BDA_DDB_FILE_NAME,
            DocumentMetadata.BDA_INVOCATION_ID: BDA_INVOCATION_UUID,
        }
    )

    result = bda_util.get_ddb_key_from_bda_output(BDA_OUTPUT_BUCKET, BDA_OUTPUT_KEY)
    assert result == BDA_DDB_FILE_NAME


def test_get_ddb_key_from_bda_output_returns_none_no_uuid(ddb_doc_metadata_table):
    """Key with no UUID segment returns None."""
    result = bda_util.get_ddb_key_from_bda_output(
        BDA_OUTPUT_BUCKET, "processed/no-uuid-here/job_metadata.json"
    )
    assert result is None


def test_get_ddb_key_from_bda_output_returns_none_no_record(ddb_doc_metadata_table):
    """Valid UUID in key but no DDB record with that invocation ID returns None."""
    result = bda_util.get_ddb_key_from_bda_output(BDA_OUTPUT_BUCKET, BDA_OUTPUT_KEY)
    assert result is None


def test_get_ddb_record_from_bda_output_returns_record(ddb_doc_metadata_table):
    """Realistic key with seeded record returns the full DDB record."""
    ddb_doc_metadata_table.put_item(
        Item={
            DocumentMetadata.FILE_NAME: BDA_DDB_FILE_NAME,
            DocumentMetadata.BDA_INVOCATION_ID: BDA_INVOCATION_UUID,
            DocumentMetadata.TENANT_ID: "test-tenant",
            DocumentMetadata.PROCESS_STATUS: ProcessStatus.STARTED.value,
        }
    )

    result = bda_util.get_ddb_record_from_bda_output(BDA_OUTPUT_BUCKET, BDA_OUTPUT_KEY)
    assert result is not None
    assert result[DocumentMetadata.FILE_NAME] == BDA_DDB_FILE_NAME
    assert result[DocumentMetadata.TENANT_ID] == "test-tenant"
    assert result[DocumentMetadata.PROCESS_STATUS] == ProcessStatus.STARTED.value


def test_get_ddb_record_from_bda_output_returns_none_no_uuid(ddb_doc_metadata_table):
    """Key with no UUID segment returns None."""
    result = bda_util.get_ddb_record_from_bda_output(
        BDA_OUTPUT_BUCKET, "processed/no-uuid/job_metadata.json"
    )
    assert result is None


def test_get_ddb_record_from_bda_output_returns_none_no_record(ddb_doc_metadata_table):
    """Valid UUID in key but no DDB record with that invocation ID returns None."""
    result = bda_util.get_ddb_record_from_bda_output(BDA_OUTPUT_BUCKET, BDA_OUTPUT_KEY)
    assert result is None
