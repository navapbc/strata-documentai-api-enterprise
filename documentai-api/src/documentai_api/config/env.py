from __future__ import annotations

import os
from functools import lru_cache

import boto3
from pydantic_settings import BaseSettings, SettingsConfigDict

from documentai_api.config.env_var_names_generated import EnvVarNames


class PydanticBaseEnvConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def _require(self, value: str | None, name: str) -> str:
        if not value:
            raise ValueError(f"{name} is not configured")
        return value


class EnvConfig(PydanticBaseEnvConfig):
    # =========================================================================
    # Environment variables
    # =========================================================================

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

    # Cognito
    cognito_user_pool_id: str | None = None
    cognito_client_id: str | None = None

    # Document AI core
    documentai_document_metadata_table_name: str | None = None
    documentai_document_metadata_job_id_index_name: str | None = None
    documentai_document_metadata_tenant_index_name: str | None = None
    documentai_document_metadata_batch_id_index_name: str | None = None
    documentai_document_metadata_status_created_at_index_name: str | None = None
    documentai_document_metadata_bda_invocation_id_index_name: str | None = None
    documentai_document_batches_table_name: str | None = None
    documentai_input_location: str | None = None
    documentai_demo_input_location: str | None = None
    documentai_output_location: str | None = None
    documentai_preprocessing_location: str | None = None
    documentai_build_table_name: str | None = None

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

    # =========================================================================
    # Accessor methods
    # =========================================================================
    def get_bda_project_arns(self) -> dict[str, str]:
        """Return a mapping of category slug -> project ARN for all configured categories.

        There is no catch-all/default project: every PreclassificationCategory
        without a matching env var is simply omitted. bda_project_arn (if set)
        is used as a fallback for any category missing its own
        BDA_PROJECT_ID_{CATEGORY} - a local-dev convenience for testing against
        a single BDA project instead of standing up all per-category projects.
        """
        from documentai_api.config.constants_preclassification_category_generated import (
            PreclassificationCategory,
        )

        prefix = self.bda_project_arn_prefix or ""
        arns: dict[str, str] = {}
        for category in PreclassificationCategory:
            project_id = os.getenv(f"BDA_PROJECT_ID_{category.upper()}")
            if project_id:
                arns[category.value] = f"{prefix}/{project_id}" if prefix else project_id
            elif self.bda_project_arn:
                arns[category.value] = self.bda_project_arn

        return arns

    @property
    def get_input_location(self) -> str:
        return self._require(self.documentai_input_location, EnvVarNames.DOCUMENTAI_INPUT_LOCATION)

    @property
    def get_output_location(self) -> str:
        return self._require(
            self.documentai_output_location, EnvVarNames.DOCUMENTAI_OUTPUT_LOCATION
        )

    @property
    def get_preprocessing_location(self) -> str:
        return self._require(
            self.documentai_preprocessing_location,
            EnvVarNames.DOCUMENTAI_PREPROCESSING_LOCATION,
        )

    @property
    def get_document_metadata_table_name(self) -> str:
        return self._require(
            self.documentai_document_metadata_table_name,
            EnvVarNames.DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME,
        )

    @property
    def get_document_metadata_job_id_index_name(self) -> str:
        return self._require(
            self.documentai_document_metadata_job_id_index_name,
            EnvVarNames.DOCUMENTAI_DOCUMENT_METADATA_JOB_ID_INDEX_NAME,
        )

    @property
    def get_document_metadata_batch_id_index_name(self) -> str:
        return self._require(
            self.documentai_document_metadata_batch_id_index_name,
            EnvVarNames.DOCUMENTAI_DOCUMENT_METADATA_BATCH_ID_INDEX_NAME,
        )

    @property
    def get_document_metadata_bda_invocation_id_index_name(self) -> str:
        return self._require(
            self.documentai_document_metadata_bda_invocation_id_index_name,
            EnvVarNames.DOCUMENTAI_DOCUMENT_METADATA_BDA_INVOCATION_ID_INDEX_NAME,
        )

    @property
    def get_document_batches_table_name(self) -> str:
        return self._require(
            self.documentai_document_batches_table_name,
            EnvVarNames.DOCUMENTAI_DOCUMENT_BATCHES_TABLE_NAME,
        )

    @property
    def get_document_build_table_name(self) -> str:
        return self._require(
            self.documentai_build_table_name, EnvVarNames.DOCUMENTAI_BUILD_TABLE_NAME
        )

    @property
    def get_bda_profile_arn(self) -> str:
        return self._require(self.bda_profile_arn, EnvVarNames.BDA_PROFILE_ARN)


class AppConfig(PydanticBaseEnvConfig):
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
        return bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

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
def get_env_config() -> EnvConfig:
    return EnvConfig()


@lru_cache
def get_app_config() -> AppConfig:
    return AppConfig()
