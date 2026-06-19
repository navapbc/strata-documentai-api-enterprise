import os
from enum import StrEnum
from functools import lru_cache

import boto3
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvVars(StrEnum):
    """Canonical names of environment variables read by the application.

    Use with get_required_env(), os.getenv(), os.environ[...], or
    monkeypatch.setenv() - since StrEnum members ARE str, no .value needed.
    """

    # === AWS / BDA ===
    BDA_PROJECT_ARN = "BDA_PROJECT_ARN"
    BDA_PROFILE_ARN = "BDA_PROFILE_ARN"
    BDA_REGION = "BDA_REGION"
    MAX_BDA_INVOKE_RETRY_ATTEMPTS = "MAX_BDA_INVOKE_RETRY_ATTEMPTS"
    BEDROCK_CLASSIFICATION_MODEL_ID_PARAM = "BEDROCK_CLASSIFICATION_MODEL_ID_PARAM"
    BEDROCK_CLASSIFICATION_PROMPT_PARAM = "BEDROCK_CLASSIFICATION_PROMPT_PARAM"
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
    API_KEYS_TABLE_NAME = "API_KEYS_TABLE_NAME"
    TENANTS_TABLE_NAME = "TENANTS_TABLE_NAME"
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


class PydanticBaseEnvConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class AWSEnvConfig(PydanticBaseEnvConfig):
    # BDA / Bedrock
    bda_project_arn: str | None = None
    bda_profile_arn: str | None = None
    bda_region: str = "us-east-1"
    max_bda_invoke_retry_attempts: int = 3
    bedrock_classification_model_id_param: str | None = None
    bedrock_classification_prompt_param: str | None = None
    bedrock_bounding_box_model_id_param: str | None = None

    # Image pipeline
    document_crop_param: str | None = None

    # BDA project ARNs (per preclassification category)
    preclassification_routing_param: str | None = None
    bda_project_arn_tax_documents: str | None = None
    bda_project_arn_employment_wages: str | None = None
    bda_project_arn_independent_earnings: str | None = None
    bda_project_arn_government_benefits: str | None = None
    bda_project_arn_private_benefits_and_settlements: str | None = None
    bda_project_arn_court_ordered_benefits: str | None = None
    bda_project_arn_financial_assets: str | None = None
    bda_project_arn_receipts_and_invoices: str | None = None
    bda_project_arn_recurring_bills: str | None = None
    bda_project_arn_housing_expenses: str | None = None
    bda_project_arn_debt_obligations: str | None = None
    bda_project_arn_identity_verification: str | None = None
    bda_project_arn_right_to_work: str | None = None
    bda_project_arn_all: str | None = None

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
    tenants_table_name: str | None = None
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
    api_auth_enabled: bool = False
    api_auth_allow_insecure_fallback: bool = False
    api_auth_cache_ttl: int = 300
    presigned_url_expiry_seconds: int = 900
    api_base_url: str = "http://localhost:8000"
    image_tag: str | None = None
    environment: str = "local"
    host: str = "127.0.0.1"
    port: int = 8000

    def is_hosted_env(self) -> bool:
        """Whether the app is running in a deployed (non-local) environment.

        Detected via the Lambda runtime marker (`AWS_LAMBDA_FUNCTION_NAME`, set
        automatically by AWS), which is true for every real deployment regardless of
        the `ENVIRONMENT` name. The app is deployed exclusively to Lambda today; if we
        ever host it elsewhere (ECS/EC2/etc.), extend this with that platform's signal.
        Local dev and the test suite run outside Lambda, so they are treated as non-hosted.
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
