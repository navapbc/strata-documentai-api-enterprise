"""Shared test fixtures."""

import os
from collections.abc import Generator

import pytest

from documentai_api.config.env_var_names_generated import EnvVarNames

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
def clear_config_cache(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    from documentai_api.config.env import AppConfig, EnvConfig, get_app_config, get_env_config
    from documentai_api.utils.auth import _get_pepper
    from documentai_api.utils.document_categories import _registered_categories

    # Disable .env file so monkeypatch.delenv reliably removes values
    # (pydantic-settings falls back to .env when a var is absent from os.environ)
    monkeypatch.setitem(EnvConfig.model_config, "env_file", None)
    monkeypatch.setitem(AppConfig.model_config, "env_file", None)
    get_env_config.cache_clear()
    get_app_config.cache_clear()
    _get_pepper.cache_clear()
    _registered_categories.clear()
    yield
    get_env_config.cache_clear()
    get_app_config.cache_clear()
    _get_pepper.cache_clear()
    _registered_categories.clear()


@pytest.fixture(autouse=True)
def drain_lastused_threads():
    """Drain leaked lastUsed updater threads and reset shared state.

    Any successful auth spawns a daemon thread that mutates
    ``_last_used_written_at`` and calls ``ddb.update_item``. Without draining,
    a thread from one test can inflate another test's patched call counts or
    corrupt shared state, causing intermittent failures under different
    ordering. Applied suite-wide as most requests authenticate via the
    FastAPI test client.
    """
    import threading
    import time
    import warnings

    from documentai_api.utils import auth as auth_util

    def _drain(timeout: float = 2.0) -> None:
        deadline = time.monotonic() + timeout
        for thread in threading.enumerate():
            if thread.name == auth_util._LAST_USED_THREAD_NAME and thread.is_alive():
                thread.join(timeout=max(0.0, deadline - time.monotonic()))

        # A thread still alive past the timeout means a mock likely leaked a real
        # call (e.g. an un-patched ddb.update_item). Surface it instead of silently
        # passing - a plain warning, not an error, so we don't trade a flaky failure
        # for a flaky hang on the very thread we couldn't join.
        stuck = sum(
            1
            for t in threading.enumerate()
            if t.name == auth_util._LAST_USED_THREAD_NAME and t.is_alive()
        )
        if stuck:
            warnings.warn(
                f"{stuck} lastUsed updater thread(s) did not drain within {timeout}s "
                "- a mock may be leaking a real call",
                stacklevel=2,
            )

    _drain()
    auth_util._last_used_written_at.clear()
    yield
    _drain()
    auth_util._last_used_written_at.clear()


@pytest.fixture
def runtime_required_env(monkeypatch, s3_bucket, ddb_doc_metadata_table):
    """Required configuration to run the application in general."""
    monkeypatch.setenv(EnvVarNames.BDA_PROFILE_ARN, "arn:aws:profile")
    monkeypatch.setenv(EnvVarNames.BDA_PROJECT_ARN_ALL, "arn:aws:project")
    monkeypatch.setenv(EnvVarNames.BDA_REGION, "us-east-1")
    monkeypatch.setenv(EnvVarNames.DOCUMENTAI_INPUT_LOCATION, f"s3://{s3_bucket.name}/input")
    monkeypatch.setenv(EnvVarNames.DOCUMENTAI_OUTPUT_LOCATION, f"s3://{s3_bucket.name}/output")
    monkeypatch.setenv(
        EnvVarNames.DOCUMENTAI_PREPROCESSING_LOCATION, f"s3://{s3_bucket.name}/preprocessing"
    )
    monkeypatch.setenv(EnvVarNames.API_AUTH_INSECURE_SHARED_KEY, "test-key")
    monkeypatch.setenv(EnvVarNames.ENVIRONMENT, "test")


@pytest.fixture
def api_client(runtime_required_env):
    """Create test client."""
    from fastapi.testclient import TestClient

    from documentai_api.app import app

    return TestClient(app)


@pytest.fixture(autouse=True)
def _cleanup_jwt():
    yield
    from documentai_api.app import app
    from documentai_api.utils.jwt_auth import verify_jwt

    app.dependency_overrides.pop(verify_jwt, None)


@pytest.fixture
def disable_auth():
    """Disable API key authentication and tenant validation for tests."""
    from documentai_api.app import app
    from documentai_api.routers.demo import _resolve_demo_context
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
    monkeypatch.setenv(EnvVarNames.API_AUTH_INSECURE_SHARED_KEY, key)
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
    monkeypatch.setenv(EnvVarNames.GLUE_DATABASE_NAME, "test_db")
    monkeypatch.setenv(EnvVarNames.DDB_RAW_DATA_TABLE_NAME, "test_table")
    monkeypatch.setenv(EnvVarNames.ATHENA_WORKGROUP_NAME, "test_workgroup")
    monkeypatch.setenv(EnvVarNames.DDB_EXPORT_BUCKET_NAME, "test-bucket")

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
    "tests.helpers.fixtures.cognito",
    "tests.helpers.fixtures.db.ddb",
    "tests.helpers.fixtures.documents",
)
