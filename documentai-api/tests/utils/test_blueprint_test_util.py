"""Tests for utils/blueprint_test.py."""

import json

import pytest

from documentai_api.config.env import EnvVars
from documentai_api.utils.blueprint_test import (
    BlueprintTestMetadata,
    cleanup_test,
    get_test_metadata,
    metadata_key,
    store_test_metadata,
)

TEST_ID = "test-id"
INVOCATION_ARN = "arn:aws:bedrock:us-east-1:123:invocation/abc"
TENANT_ID = "tenant-a"
DOCUMENT_TYPE = "w2"
TEST_KEY = "test-runner/test-id/doc.pdf"


@pytest.fixture(autouse=True)
def _set_input_bucket_env(s3_bucket, monkeypatch):
    monkeypatch.setenv(EnvVars.DOCUMENTAI_INPUT_LOCATION, f"s3://{s3_bucket.name}/input")


# =============================================================================
# metadata_key
# =============================================================================


def test_metadata_key_format():
    assert metadata_key("test-metadata-key") == "test-runner/test-metadata-key/metadata.json"


# =============================================================================
# store_test_metadata / get_test_metadata round-trip
# =============================================================================


@pytest.mark.parametrize(
    ("tenant_id", "document_type", "expected_tenant", "expected_doc_type"),
    [
        (TENANT_ID, DOCUMENT_TYPE, TENANT_ID, DOCUMENT_TYPE),
        (TENANT_ID, None, TENANT_ID, None),
        (None, DOCUMENT_TYPE, "", DOCUMENT_TYPE),
    ],
)
def test_store_and_get_metadata_round_trip(
    tenant_id, document_type, expected_tenant, expected_doc_type
):
    store_test_metadata(TEST_ID, INVOCATION_ARN, tenant_id, document_type, TEST_KEY)
    result = get_test_metadata(TEST_ID)

    assert isinstance(result, BlueprintTestMetadata)
    assert result.invocation_arn == INVOCATION_ARN
    assert result.tenant_id == expected_tenant

    if expected_doc_type is None:
        assert result.document_type is None
    else:
        assert result.document_type == expected_doc_type

    assert result.test_key == TEST_KEY


def test_get_metadata_stores_correct_s3_key(s3_bucket):
    store_test_metadata(TEST_ID, INVOCATION_ARN, TENANT_ID, DOCUMENT_TYPE, TEST_KEY)

    obj = s3_bucket.Object(metadata_key(TEST_ID)).get()
    data = json.loads(obj["Body"].read())

    assert data["invocationArn"] == INVOCATION_ARN
    assert data["tenantId"] == TENANT_ID
    assert data["documentType"] == DOCUMENT_TYPE
    assert data["testKey"] == TEST_KEY


# =============================================================================
# get_test_metadata - missing / corrupt
# =============================================================================


def test_get_metadata_returns_none_when_missing():
    result = get_test_metadata("nonexistent-id")
    assert result is None


def test_get_metadata_returns_none_on_corrupt_json(s3_bucket):
    s3_bucket.put_object(Key=metadata_key(TEST_ID), Body=b"{not valid json")
    result = get_test_metadata(TEST_ID)
    assert result is None


# =============================================================================
# cleanup_test
# =============================================================================


def test_cleanup_test_deletes_file(s3_bucket):
    import boto3
    from botocore.exceptions import ClientError

    s3_bucket.put_object(Key=TEST_KEY, Body=b"content")
    cleanup_test(TEST_ID, TEST_KEY)

    s3 = boto3.client("s3", region_name="us-east-1")
    with pytest.raises(ClientError, match="NoSuchKey"):
        s3.get_object(Bucket=s3_bucket.name, Key=TEST_KEY)


def test_cleanup_test_does_not_raise_on_missing_file():
    cleanup_test(TEST_ID, "nonexistent/key.pdf")  # should not raise
