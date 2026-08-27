import os
from enum import StrEnum
from functools import lru_cache

import boto3
from pydantic_settings import BaseSettings, SettingsConfigDict

from documentai_api.config.constants import BDA_PROJECT_KEY_ALL


class EnvVars(StrEnum):
    """Canonical names of environment variables read by the application.

    Use with get_required_env(), os.getenv(), os.environ[...], or
    monkeypatch.setenv() - since StrEnum members ARE str, no .value needed.
    """

    # === AWS / BDA ===
    BDA_PROJECT_ARN_ALL = "BDA_PROJECT_ARN_ALL"
    BDA_PROFILE_ARN = "BDA_PROFILE_ARN"
    BDA_REGION = "BDA_REGION"
    MAX_BDA_INVOKE_RETRY_ATTEMPTS = "MAX_BDA_INVOKE_RETRY_ATTEMPTS"
    BEDROCK_CLASSIFICATION_MODEL_ID_PARAM = "BEDROCK_CLASSIFICATION_MODEL_ID_PARAM"
    BEDROCK_BOUNDING_BOX_MODEL_ID_PARAM = "BEDROCK_BOUNDING_BOX_MODEL_ID_PARAM"

    # === Document AI core ===
    DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME = "DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME"
    DOCUMENTAI_DOCUMENT_METADATA_JOB_ID_INDEX_NAME = (
        "DOCUMENTAI_DOCUMENT_METADATA_JOB_ID_INDEX_NAME"
    )
    DOCUMENTAI_DOCUMENT_METADATA_BDA_INVOCATION_ID_INDEX_NAME = (
        "DOCUMENTAI_DOCUMENT_METADATA_BDA_INVOCATION_ID_INDEX_NAME"
    )
    DOCUMENTAI_DOCUMENT_METADATA_TENANT_INDEX_NAME = (
        "DOCUMENTAI_DOCUMENT_METADATA_TENANT_INDEX_NAME"
    )
    DOCUMENTAI_INPUT_LOCATION = "DOCUMENTAI_INPUT_LOCATION"
    DOCUMENTAI_DEMO_INPUT_LOCATION = "DOCUMENTAI_DEMO_INPUT_LOCATION"
    DOCUMENTAI_OUTPUT_LOCATION = "DOCUMENTAI_OUTPUT_LOCATION"
    DOCUMENTAI_PREPROCESSING_LOCATION = "DOCUMENTAI_PREPROCESSING_LOCATION"

    # === Document AI document batch core ===
    DOCUMENTAI_DOCUMENT_METADATA_BATCH_ID_INDEX_NAME = (
        "DOCUMENTAI_DOCUMENT_METADATA_BATCH_ID_INDEX_NAME"
    )
    DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME = "DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME"

    # === Document AI document build core ===
    DOCUMENTAI_BUILD_TABLE_NAME = "DOCUMENTAI_BUILD_TABLE_NAME"

    # === Auth / API keys ===
    API_AUTH_INSECURE_SHARED_KEY = "API_AUTH_INSECURE_SHARED_KEY"
    API_AUTH_INSECURE_SHARED_KEY_PARAM = "API_AUTH_INSECURE_SHARED_KEY_PARAM"
    API_AUTH_ENABLED = "API_AUTH_ENABLED"
    API_AUTH_CACHE_TTL = "API_AUTH_CACHE_TTL"
    API_KEY_PEPPER_PARAM = "API_KEY_PEPPER_PARAM"
    API_KEYS_TABLE_NAME = "API_KEYS_TABLE_NAME"
    API_KEYS_TENANT_INDEX_NAME = "API_KEYS_TENANT_INDEX_NAME"
    TENANTS_TABLE_NAME = "TENANTS_TABLE_NAME"
    TENANT_REQUEST_COUNTS_TABLE_NAME = "TENANT_REQUEST_COUNTS_TABLE_NAME"
    AUDIT_EVENTS_TABLE_NAME = "AUDIT_EVENTS_TABLE_NAME"

    # === Extraction rules ===
    EXTRACTION_RULES_TABLE_NAME = "EXTRACTION_RULES_TABLE_NAME"
    DOCUMENT_CATEGORIES_TABLE_NAME = "DOCUMENT_CATEGORIES_TABLE_NAME"

    # === Metrics pipeline ===
    ATHENA_WORKGROUP_NAME = "ATHENA_WORKGROUP_NAME"
    DDB_EXPORT_BUCKET_NAME = "DDB_EXPORT_BUCKET_NAME"
    DDB_METRICS_INPUT_QUEUE_URL = "DDB_METRICS_INPUT_QUEUE_URL"
    DDB_RAW_DATA_TABLE_NAME = "DDB_RAW_DATA_TABLE_NAME"
    GLUE_DATABASE_NAME = "GLUE_DATABASE_NAME"

    # === App runtime ===
    IMAGE_TAG = "IMAGE_TAG"
    ENVIRONMENT = "ENVIRONMENT"
    HOST = "HOST"
    PORT = "PORT"
    AWS_LAMBDA_FUNCTION_NAME = "AWS_LAMBDA_FUNCTION_NAME"  # set automatically by the Lambda runtime

    # === OpenTelemetry ===
    OTEL_SDK_DISABLED = "OTEL_SDK_DISABLED"
    OTEL_SERVICE_NAME = "OTEL_SERVICE_NAME"
    OTEL_EXPORTER_OTLP_ENDPOINT = "OTEL_EXPORTER_OTLP_ENDPOINT"


class PydanticBaseEnvConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class AWSEnvConfig(PydanticBaseEnvConfig):
    # SSM
    ssm_prefix: str | None = None

    # BDA / Bedrock
    bda_project_arn: str | None = None
    bda_profile_arn: str | None = None
    bda_region: str = "us-east-1"
    max_bda_invoke_retry_attempts: int = 3
    bedrock_classification_model_id_param: str | None = None
    bedrock_bounding_box_model_id_param: str | None = None
    bedrock_blur_quadrant_model_id_param: str | None = None
    bedrock_supplemental_extraction_model_id_param: str | None = None

    # BDA project ARNs (per preclassification category)
    # Resolved dynamically from PreclassificationCategory rather than hand-maintained.
    bda_project_arn_prefix: str | None = None
    bda_project_arn_all: str | None = None

    def get_bda_project_arns(self) -> dict[str, str]:
        """Return a mapping of category slug -> project ARN for all configured categories."""
        from documentai_api.config.constants_preclassification_category_generated import (
            PreclassificationCategory,
        )

        prefix = self.bda_project_arn_prefix or ""
        arns: dict[str, str] = {}
        for category in PreclassificationCategory:
            project_id = os.getenv(f"BDA_PROJECT_ID_{category.upper()}")
            if project_id:
                arns[category.value] = f"{prefix}/{project_id}" if prefix else project_id
        if self.bda_project_arn_all:
            arns[BDA_PROJECT_KEY_ALL] = self.bda_project_arn_all
        elif self.bda_project_arn:
            arns[BDA_PROJECT_KEY_ALL] = self.bda_project_arn

        return arns

    # Cognito
    cognito_user_pool_id: str | None = None
    cognito_client_id: str | None = None

    # Document AI core
    documentai_document_metadata_table_name: str | None = None
    documentai_document_metadata_job_id_index_name: str | None = None
    documentai_document_metadata_tenant_index_name: str | None = None
    documentai_document_metadata_batch_id_index_name: str | None = None
    documentai_document_batches_table_name: str | None = None
    documentai_input_location: str | None = None
    documentai_demo_input_location: str | None = None
    documentai_output_location: str | None = None

    # Auth / API keys
    api_keys_table_name: str | None = None
    api_keys_tenant_index_name: str | None = None
    tenants_table_name: str | None = None
    tenant_request_counts_table_name: str | None = None
    audit_events_table_name: str | None = None

    # Extraction rules
    extraction_rules_table_name: str | None = None
    document_categories_table_name: str | None = None

    # Metrics pipeline
    athena_workgroup_name: str | None = None
    ddb_export_bucket_name: str | None = None
    ddb_metrics_input_queue_url: str | None = None
    ddb_raw_data_table_name: str | None = None
    glue_database_name: str | None = None


class AppEnvConfig(PydanticBaseEnvConfig):
    api_auth_insecure_shared_key: str = ""
    api_auth_insecure_shared_key_param: str | None = None
    api_key_pepper_param: str | None = None
    api_auth_enabled: bool = False
    api_auth_cache_ttl: int = 300
    presigned_url_expiry_seconds: int = 900
    api_base_url: str = "http://localhost:8000"
    cors_allowed_origins: list[str] = []

    def get_cors_origins(self) -> list[str]:
        """Return configured origins, or ["*"] in non-hosted environments."""
        if self.cors_allowed_origins:
            return self.cors_allowed_origins

        return [] if self.is_hosted_env() else ["*"]

    image_tag: str | None = None
    environment: str = "local"
    host: str = "127.0.0.1"
    port: int = 8000

    def is_hosted_env(self) -> bool:
        """Whether the app is running in a deployed (non-local) environment.

        Detected solely via the Lambda runtime marker (`AWS_LAMBDA_FUNCTION_NAME`,
        set automatically by AWS). This ensures local/test runs are never treated
        as hosted regardless of the ENVIRONMENT variable value.
        """
        return bool(os.environ.get(EnvVars.AWS_LAMBDA_FUNCTION_NAME))

    def resolve_insecure_shared_key(self) -> str:
        """Resolve the insecure shared key from SSM if param is set, else use env var."""
        if self.api_auth_insecure_shared_key:
            return self.api_auth_insecure_shared_key

        if self.api_auth_insecure_shared_key_param:
            ssm = boto3.client("ssm")
            response = ssm.get_parameter(
                Name=self.api_auth_insecure_shared_key_param, WithDecryption=True
            )
            return response["Parameter"]["Value"]
        return ""

    def resolve_api_key_pepper(self) -> str | None:
        """Resolve the API key pepper from SSM SecureString. Returns None if not configured."""
        if not self.api_key_pepper_param:
            return None
        ssm = boto3.client("ssm")
        response = ssm.get_parameter(Name=self.api_key_pepper_param, WithDecryption=True)
        return response["Parameter"]["Value"]


@lru_cache
def get_aws_config() -> AWSEnvConfig:
    return AWSEnvConfig()


@lru_cache
def get_app_env_config() -> AppEnvConfig:
    return AppEnvConfig()


def get_required_env(name: EnvVars) -> str:
    """Read an env var, raising ValueError if not set."""
    value = os.getenv(name)

    if not value:
        raise ValueError(f"{name} environment variable not set")

    return value
