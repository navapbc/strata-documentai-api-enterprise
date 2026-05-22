import os
from enum import StrEnum
from functools import lru_cache

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

    # === Document AI core ===
    DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME = "DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME"
    DOCUMENTAI_DOCUMENT_METADATA_JOB_ID_INDEX_NAME = (
        "DOCUMENTAI_DOCUMENT_METADATA_JOB_ID_INDEX_NAME"
    )
    DOCUMENTAI_INPUT_LOCATION = "DOCUMENTAI_INPUT_LOCATION"
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
    API_AUTH_ENABLED = "API_AUTH_ENABLED"
    API_AUTH_CACHE_TTL = "API_AUTH_CACHE_TTL"
    API_KEYS_TABLE_NAME = "API_KEYS_TABLE_NAME"

    # === Extraction rules ===
    EXTRACTION_RULES_TABLE_NAME = "EXTRACTION_RULES_TABLE_NAME"

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

    # Document AI core
    documentai_document_metadata_table_name: str | None = None
    documentai_document_metadata_job_id_index_name: str | None = None
    documentai_document_metadata_batch_id_index_name: str | None = None
    documentai_document_batches_table_name: str | None = None
    documentai_input_location: str | None = None
    documentai_output_location: str | None = None

    # Auth / API keys
    api_keys_table_name: str | None = None

    # Extraction rules
    extraction_rules_table_name: str | None = None

    # Metrics pipeline
    athena_workgroup_name: str | None = None
    ddb_export_bucket_name: str | None = None
    ddb_metrics_input_queue_url: str | None = None
    ddb_raw_data_table_name: str | None = None
    glue_database_name: str | None = None


class AppEnvConfig(PydanticBaseEnvConfig):
    api_auth_insecure_shared_key: str = ""
    api_auth_enabled: bool = False
    api_auth_cache_ttl: int = 300
    presigned_url_expiry_seconds: int = 900
    api_base_url: str = "http://localhost:8000"
    image_tag: str | None = None
    environment: str = "local"
    host: str = "127.0.0.1"
    port: int = 8000


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
