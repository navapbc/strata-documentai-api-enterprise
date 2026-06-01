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
