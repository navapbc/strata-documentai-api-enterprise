import pytest


@pytest.fixture
def ddb_doc_metadata_table(ddb_doc_metadata_table_resource, set_ddb_doc_metadata_table_env_vars):
    return ddb_doc_metadata_table_resource


@pytest.fixture
def ddb_doc_metadata_table_resource(aws_credentials):
    """Create a test DynamoDB table."""
    import boto3
    from moto import mock_aws

    with mock_aws():
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.create_table(
            TableName="metadata",
            KeySchema=[{"AttributeName": "fileName", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "fileName", "AttributeType": "S"},
                {"AttributeName": "jobId", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "job-id-index",
                    "KeySchema": [{"AttributeName": "jobId", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table


@pytest.fixture
def extraction_rules_table(aws_credentials, monkeypatch):
    from moto import mock_aws

    with mock_aws():
        import boto3

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
        monkeypatch.setenv("EXTRACTION_RULES_TABLE_NAME", table.name)
        yield table


@pytest.fixture
def api_keys_table(aws_credentials, monkeypatch):
    from moto import mock_aws

    with mock_aws():
        import boto3

        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="api-keys",
            KeySchema=[{"AttributeName": "keyHash", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "keyHash", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        monkeypatch.setenv("API_KEYS_TABLE_NAME", table.name)
        yield table


@pytest.fixture
def set_ddb_doc_metadata_table_env_vars(ddb_doc_metadata_table_resource, monkeypatch):
    from documentai_api.utils import env

    monkeypatch.setenv(
        env.DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME, ddb_doc_metadata_table_resource.name
    )
    monkeypatch.setenv(env.DOCUMENTAI_DOCUMENT_METADATA_JOB_ID_INDEX_NAME, "job-id-index")
