"""Shared test fixtures."""

import os

import pytest

from documentai_api.config.env import EnvVars

#############################################################################
# Autouse fixtures                                                          #
#                                                                           #
# Since these are defined here in the top-level conftest file, they apply   #
# globally to all tests.                                                    #
#############################################################################


@pytest.fixture(autouse=True, scope="session")
def reset_env():
    """Start each test suite run with a clean environment."""
    # save a copy of environment as it is at start of run
    env = dict(os.environ)

    os.environ.clear()

    # for native dependencies
    os.environ["PATH"] = env["PATH"]

    # for other fixtures that may want to reference real environment values for
    # their test settings
    return env


@pytest.fixture
def real_aws_credentials(reset_env):
    """Restore AWS credentials cleared by the session-scoped reset_env fixture."""
    for key in (
        "HOME",
        "AWS_PROFILE",
        "AWS_DEFAULT_REGION",
        "AWS_REGION",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
    ):
        if key in reset_env:
            os.environ[key] = reset_env[key]


#######################
# API Server fixtures #
#######################


@pytest.fixture(autouse=True)
def clear_config_cache():
    from documentai_api.config.env import get_app_env_config, get_aws_config

    get_aws_config.cache_clear()
    get_app_env_config.cache_clear()
    yield
    get_aws_config.cache_clear()
    get_app_env_config.cache_clear()


@pytest.fixture
def runtime_required_env(monkeypatch, s3_bucket, ddb_doc_metadata_table):
    """Required configuration to run the application in general."""
    monkeypatch.setenv(EnvVars.BDA_PROFILE_ARN, "arn:aws:profile")
    monkeypatch.setenv(EnvVars.BDA_PROJECT_ARN, "arn:aws:project")
    monkeypatch.setenv(EnvVars.BDA_REGION, "us-east-1")
    monkeypatch.setenv(EnvVars.DOCUMENTAI_INPUT_LOCATION, f"s3://{s3_bucket.name}/input")
    monkeypatch.setenv(EnvVars.DOCUMENTAI_OUTPUT_LOCATION, f"s3://{s3_bucket.name}/output")
    monkeypatch.setenv(
        EnvVars.DOCUMENTAI_PREPROCESSING_LOCATION, f"s3://{s3_bucket.name}/preprocessing"
    )
    monkeypatch.setenv(EnvVars.API_AUTH_INSECURE_SHARED_KEY, "test-key")
    monkeypatch.setenv(EnvVars.ENVIRONMENT, "test")


@pytest.fixture
def api_client(runtime_required_env):
    """Create test client."""
    from fastapi.testclient import TestClient

    from documentai_api.app import app

    return TestClient(app)


@pytest.fixture
def disable_auth():
    """Disable API key authentication and tenant validation for tests."""
    from documentai_api.app import app
    from documentai_api.app_demo import _resolve_demo_context
    from documentai_api.utils.auth import (
        UserContext,
        get_user_context_from_api_key,
        get_user_context_with_fallback,
        verify_api_key,
    )
    from documentai_api.utils.tenant_access import (
        validate_batch_tenant_access,
        validate_build_tenant_access,
    )

    mock_context = UserContext(tenant_id="test-tenant", api_key_name="test-client")
    mock_demo_context = UserContext(tenant_id="demo-test-sub", api_key_name="test@example.com")
    app.dependency_overrides[verify_api_key] = lambda: mock_context
    app.dependency_overrides[get_user_context_from_api_key] = lambda: mock_context
    app.dependency_overrides[get_user_context_with_fallback] = lambda: mock_context
    app.dependency_overrides[_resolve_demo_context] = lambda: mock_demo_context
    app.dependency_overrides[validate_batch_tenant_access] = lambda: None
    app.dependency_overrides[validate_build_tenant_access] = lambda: None
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def api_skeleton_key(monkeypatch):
    key = "foobar"
    monkeypatch.setenv(EnvVars.API_AUTH_INSECURE_SHARED_KEY, key)
    return key


#################################################################################
# Regular fixtures                                                              #
#                                                                               #
# Logical groups of fixtures should be grouped in tests/helpers/fixtures/ (and  #
# then imported at the bottom of this file) or live within conftest.py files in #
# various test directories. But general/misc. fixtures can live here.           #
#################################################################################


@pytest.fixture
def mock_metrics_aggregator_env(mocker, monkeypatch):
    """Mock environment and Athena dependencies for metrics aggregator tests."""
    monkeypatch.setenv(EnvVars.GLUE_DATABASE_NAME, "test_db")
    monkeypatch.setenv(EnvVars.DDB_RAW_DATA_TABLE_NAME, "test_table")
    monkeypatch.setenv(EnvVars.ATHENA_WORKGROUP_NAME, "test_workgroup")
    monkeypatch.setenv(EnvVars.DDB_EXPORT_BUCKET_NAME, "test-bucket")

    mock_athena = mocker.patch("documentai_api.jobs.metrics_aggregator.main._execute_athena_query")
    mock_results = mocker.patch("documentai_api.jobs.metrics_aggregator.main._get_athena_results")
    mock_athena.return_value = "test-query-execution-id"
    mock_results.return_value = [
        {"process_status": "success", "created_at": "2026-02-20T10:00:00Z"}
    ]
    return {"mock_athena": mock_athena, "mock_results": mock_results}


@pytest.fixture
def disable_tenacity_wait(mocker):
    """Make Tenacity wait for 0 seconds between retries.

    Generally
    """
    mocker.patch("tenacity.nap.time")


@pytest.fixture
def clear_env_vars():
    """Clear all environment variables.

    The test suite starts with an _almost_ clean environment by default, by if
    you want it cleaner you can use this. Pytest may internally still set some
    environment variables.
    """
    import os
    from unittest.mock import patch

    with patch.dict(os.environ, {}, clear=True):
        yield


######################
# Pytest setup stuff #
######################

pytest.register_assert_rewrite("tests.helpers")

pytest_plugins = (
    "tests.helpers.fixtures.aws",
    "tests.helpers.fixtures.bda",
    "tests.helpers.fixtures.db.ddb",
    "tests.helpers.fixtures.documents",
)
