import boto3
import pytest
from moto import mock_aws

from documentai_api.config.env import EnvVars


@pytest.fixture
def ddb_doc_metadata_table(ddb_doc_metadata_table_resource, set_ddb_doc_metadata_table_env_vars):
    return ddb_doc_metadata_table_resource


@pytest.fixture
def ddb_doc_metadata_table_resource(aws_credentials):
    """Create a test DynamoDB table."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.create_table(
            TableName="metadata",
            KeySchema=[{"AttributeName": "fileName", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "fileName", "AttributeType": "S"},
                {"AttributeName": "jobId", "AttributeType": "S"},
                {"AttributeName": "batchId", "AttributeType": "S"},
                {"AttributeName": "bdaInvocationId", "AttributeType": "S"},
                {"AttributeName": "tenantId", "AttributeType": "S"},
                {"AttributeName": "createdAt", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "job-id-index",
                    "KeySchema": [{"AttributeName": "jobId", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "batch-id-index",
                    "KeySchema": [{"AttributeName": "batchId", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "bda-inv-index",
                    "KeySchema": [{"AttributeName": "bdaInvocationId", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "tenant-index",
                    "KeySchema": [
                        {"AttributeName": "tenantId", "KeyType": "HASH"},
                        {"AttributeName": "createdAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table


@pytest.fixture
def extraction_rules_table(aws_credentials, monkeypatch):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="extraction-rules",
            KeySchema=[
                {"AttributeName": "tenantId", "KeyType": "HASH"},
                {"AttributeName": "documentType", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "tenantId", "AttributeType": "S"},
                {"AttributeName": "documentType", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        monkeypatch.setenv(EnvVars.EXTRACTION_RULES_TABLE_NAME, table.name)
        yield table


@pytest.fixture
def document_build_ddb_table(aws_credentials, monkeypatch):
    """Create a moto-backed document-builds table and point env vars at it."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="document-builds",
            KeySchema=[
                {"AttributeName": "buildId", "KeyType": "HASH"},
                {"AttributeName": "pageNumber", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "buildId", "AttributeType": "S"},
                {"AttributeName": "pageNumber", "AttributeType": "N"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        monkeypatch.setenv(EnvVars.DOCUMENTAI_BUILD_TABLE_NAME, table.name)
        monkeypatch.setenv(
            EnvVars.DOCUMENTAI_PREPROCESSING_LOCATION, "s3://test-bucket/preprocessing"
        )
        yield table


@pytest.fixture
def ddb_batches_table(aws_credentials, monkeypatch):
    """Create a moto-backed document-batches table and point env vars at it."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="document-batches",
            KeySchema=[{"AttributeName": "batchId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "batchId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        monkeypatch.setenv(EnvVars.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME, table.name)
        yield table


@pytest.fixture
def api_keys_table(aws_credentials, monkeypatch):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="api-keys",
            KeySchema=[{"AttributeName": "keyHash", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "keyHash", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        monkeypatch.setenv(EnvVars.API_KEYS_TABLE_NAME, table.name)
        yield table


@pytest.fixture
def set_ddb_doc_metadata_table_env_vars(ddb_doc_metadata_table_resource, monkeypatch):

    monkeypatch.setenv(
        EnvVars.DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME, ddb_doc_metadata_table_resource.name
    )
    monkeypatch.setenv(EnvVars.DOCUMENTAI_DOCUMENT_METADATA_JOB_ID_INDEX_NAME, "job-id-index")
    monkeypatch.setenv(EnvVars.DOCUMENTAI_DOCUMENT_METADATA_BATCH_ID_INDEX_NAME, "batch-id-index")
    monkeypatch.setenv(
        EnvVars.DOCUMENTAI_DOCUMENT_METADATA_BDA_INVOCATION_ID_INDEX_NAME, "bda-inv-index"
    )
    monkeypatch.setenv(EnvVars.DOCUMENTAI_DOCUMENT_METADATA_TENANT_INDEX_NAME, "tenant-index")
    monkeypatch.setenv(EnvVars.DOCUMENTAI_INPUT_LOCATION, "s3://test/input")
    monkeypatch.setenv(EnvVars.DOCUMENTAI_OUTPUT_LOCATION, "s3://test/output")
    monkeypatch.setenv(EnvVars.BDA_PROJECT_ARN_ALL, "arn:aws:test")
    monkeypatch.setenv(EnvVars.BDA_PROFILE_ARN, "arn:aws:test")


@pytest.fixture
def tenants_table(aws_credentials, monkeypatch):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="tenants",
            KeySchema=[{"AttributeName": "tenantId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "tenantId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        monkeypatch.setenv(EnvVars.TENANTS_TABLE_NAME, table.name)
        yield table


@pytest.fixture
def audit_events_table(aws_credentials, monkeypatch):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="audit-events",
            KeySchema=[
                {"AttributeName": "tenantId", "KeyType": "HASH"},
                {"AttributeName": "timestamp#eventId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "tenantId", "AttributeType": "S"},
                {"AttributeName": "timestamp#eventId", "AttributeType": "S"},
                {"AttributeName": "action", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "action-timestamp-index",
                    "KeySchema": [
                        {"AttributeName": "action", "KeyType": "HASH"},
                        {"AttributeName": "timestamp#eventId", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        monkeypatch.setenv(EnvVars.AUDIT_EVENTS_TABLE_NAME, table.name)
        yield table
