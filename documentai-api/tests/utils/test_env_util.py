"""Tests for utils/env.py."""

import pytest

from documentai_api.config.env import AppEnvConfig, AWSEnvConfig, EnvVars


@pytest.fixture(autouse=True)
def _no_lambda_marker(monkeypatch):
    """Ensure the Lambda runtime marker is absent unless a test sets it."""
    monkeypatch.delenv(EnvVars.AWS_LAMBDA_FUNCTION_NAME, raising=False)


def test_aws_env_config_has_required_fields():
    fields = AWSEnvConfig.model_fields
    assert "bda_project_arn" in fields
    assert "bda_profile_arn" in fields
    assert "documentai_input_location" in fields
    assert "documentai_output_location" in fields
    assert "documentai_document_metadata_table_name" in fields
    assert "documentai_document_metadata_job_id_index_name" in fields


def test_aws_env_config_defaults():
    fields = AWSEnvConfig.model_fields | AppEnvConfig.model_fields
    assert fields["bda_region"].default == "us-east-1"
    assert fields["max_bda_invoke_retry_attempts"].default == 3


##############################################################################
# AppEnvConfig.is_hosted_env
##############################################################################


def test_is_hosted_env_false_off_lambda():
    """Off-Lambda is never hosted - and the ENVIRONMENT name must not change that.

    The `prod` case guards against reintroducing name-based detection, which would
    let a hosted environment's name (rather than the runtime) decide auth enforcement.
    """
    assert AppEnvConfig(environment="local").is_hosted_env() is False
    assert AppEnvConfig(environment="prod").is_hosted_env() is False


def test_is_hosted_env_true_in_lambda(monkeypatch):
    """The Lambda runtime marker is the sole signal, regardless of ENVIRONMENT name."""
    monkeypatch.setenv(EnvVars.AWS_LAMBDA_FUNCTION_NAME, "documentai-api")
    assert AppEnvConfig(environment="local").is_hosted_env() is True


##############################################################################
# AWSEnvConfig.get_bda_project_arns
##############################################################################


def test_get_bda_project_arns_builds_from_prefix_and_ids(monkeypatch):
    """Reconstructs full ARNs from BDA_PROJECT_ARN_PREFIX + BDA_PROJECT_ID_{CATEGORY}."""
    from documentai_api.config.constants_preclassification_category_generated import (
        PreclassificationCategory,
    )

    prefix = "arn:aws:bedrock:us-east-1:123456789012:data-automation-project"
    monkeypatch.setenv("BDA_PROJECT_ARN_PREFIX", prefix)
    monkeypatch.setenv("BDA_PROJECT_ID_EMPLOYER_INCOME", "abc-123")
    monkeypatch.setenv("BDA_PROJECT_ARN_ALL", f"{prefix}/all-456")

    config = AWSEnvConfig(bda_project_arn_all=f"{prefix}/all-456")
    arns = config.get_bda_project_arns()

    assert arns[PreclassificationCategory.EMPLOYER_INCOME] == f"{prefix}/abc-123"
    assert arns["all"] == f"{prefix}/all-456"


def test_get_bda_project_arns_omits_unconfigured_categories(monkeypatch):
    """Categories without a BDA_PROJECT_ID_* env var are not included."""
    monkeypatch.setenv(
        "BDA_PROJECT_ARN_PREFIX", "arn:aws:bedrock:us-east-1:123:data-automation-project"
    )
    monkeypatch.setenv("BDA_PROJECT_ID_IDENTITY", "id-789")

    config = AWSEnvConfig()
    arns = config.get_bda_project_arns()

    assert "identity" in arns
    assert "employer_income" not in arns
    assert "all" not in arns


def test_get_bda_project_arns_falls_back_to_bda_project_arn(monkeypatch):
    """Falls back to bda_project_arn when bda_project_arn_all is not set."""
    prefix = "arn:aws:bedrock:us-east-1:123:data-automation-project"
    monkeypatch.setenv("BDA_PROJECT_ARN_PREFIX", prefix)

    config = AWSEnvConfig(bda_project_arn=f"{prefix}/fallback-arn")
    arns = config.get_bda_project_arns()

    assert arns["all"] == f"{prefix}/fallback-arn"
