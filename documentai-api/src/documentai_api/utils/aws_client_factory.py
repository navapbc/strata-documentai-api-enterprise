from __future__ import annotations

import os
from functools import lru_cache
from typing import TYPE_CHECKING

import boto3

from documentai_api.logging import get_logger

if TYPE_CHECKING:
    from mypy_boto3_athena import AthenaClient
    from mypy_boto3_bedrock_data_automation.client import DataAutomationforBedrockClient
    from mypy_boto3_bedrock_data_automation_runtime.client import (
        RuntimeforBedrockDataAutomationClient,
    )
    from mypy_boto3_bedrock_runtime.client import BedrockRuntimeClient
    from mypy_boto3_cognito_idp import CognitoIdentityProviderClient
    from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table
    from mypy_boto3_s3.client import S3Client
    from mypy_boto3_sqs import SQSClient
    from mypy_boto3_ssm.client import SSMClient


logger = get_logger(__name__)


class AWSClientFactory:
    _session: boto3.Session | None = None

    @classmethod
    def get_session(cls) -> boto3.Session:
        if cls._session is None:
            cls._session = boto3.Session()

        return cls._session

    @classmethod
    def get_region(cls) -> str:
        return os.getenv("AWS_REGION", "us-east-1")

    @classmethod
    def _get_bda_region(cls) -> str:
        from documentai_api.config import env

        return env.get_aws_config().bda_region

    @classmethod
    def _get_dynamodb_table(cls, table_name: str) -> Table:
        return cls.get_dynamodb_resource().Table(table_name)

    @classmethod
    @lru_cache(maxsize=1)
    def get_s3_client(cls) -> S3Client:
        return cls.get_session().client("s3", region_name=cls.get_region())

    @classmethod
    @lru_cache(maxsize=1)
    def get_dynamodb_resource(cls) -> DynamoDBServiceResource:
        return cls.get_session().resource("dynamodb", region_name=cls.get_region())

    @classmethod
    @lru_cache(maxsize=1)
    def get_bda_client(cls) -> DataAutomationforBedrockClient:
        """Get Bedrock Data Automation client for project/blueprint management."""
        return cls.get_session().client(
            "bedrock-data-automation", region_name=cls._get_bda_region()
        )

    @classmethod
    @lru_cache(maxsize=1)
    def get_bda_runtime_client(cls) -> RuntimeforBedrockDataAutomationClient:
        """Get Bedrock Data Automation Runtime client for job execution (invoke, get status)."""
        return cls.get_session().client(
            "bedrock-data-automation-runtime", region_name=cls._get_bda_region()
        )

    @classmethod
    @lru_cache(maxsize=1)
    def get_bedrock_runtime_client(cls) -> BedrockRuntimeClient:
        return AWSClientFactory.get_session().client(
            "bedrock-runtime", region_name=AWSClientFactory.get_region()
        )

    @classmethod
    @lru_cache(maxsize=1)
    def get_sqs_client(cls) -> SQSClient:
        return cls.get_session().client("sqs", region_name=cls.get_region())

    @classmethod
    @lru_cache(maxsize=1)
    def get_athena_client(cls) -> AthenaClient:
        return cls.get_session().client("athena", region_name=cls.get_region())

    @classmethod
    @lru_cache(maxsize=1)
    def get_cognito_client(cls) -> CognitoIdentityProviderClient:
        return cls.get_session().client("cognito-idp", region_name=cls.get_region())

    @classmethod
    @lru_cache(maxsize=1)
    def get_ssm_client(cls) -> SSMClient:
        return cls.get_session().client("ssm", region_name=cls.get_region())

    @classmethod
    def get_ddb_table(cls, table_name: str) -> Table:
        """Get DynamoDB table resource by name."""
        return cls._get_dynamodb_table(table_name)


__all__ = ["AWSClientFactory"]
