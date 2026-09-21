from unittest.mock import MagicMock, patch

import pytest

from documentai_api.config.constants import ConfigDefaults
from documentai_api.config.env import get_env_config
from documentai_api.config.env_var_names_generated import EnvVarNames
from documentai_api.utils import bda_invoker as bda_invoker_util


@pytest.fixture(autouse=True)
def bda_env(monkeypatch):
    """Set the env vars required by invoke_bedrock_data_automation for every test."""
    monkeypatch.setenv(EnvVarNames.BDA_PROJECT_ARN, "arn:aws:project")
    monkeypatch.setenv(EnvVarNames.BDA_PROFILE_ARN, "arn:aws:profile")
    monkeypatch.setenv(EnvVarNames.DOCUMENTAI_OUTPUT_LOCATION, "s3://output-bucket/path")
    get_env_config.cache_clear()
    yield
    get_env_config.cache_clear()


def test_invoke_bedrock_data_automation_single_page():
    bda_invocation_arn = "arn:aws:invocation:123"

    with (
        patch.object(bda_invoker_util, "_project_arns_cache", None),
        patch(
            "documentai_api.utils.bda_invoker.AWSClientFactory.get_bda_runtime_client"
        ) as mock_get_bda_client,
        patch("documentai_api.services.s3.get_file_bytes") as mock_get_file_bytes,
        patch(
            "documentai_api.utils.bda_invoker.document_utils.get_page_count"
        ) as mock_get_page_count,
    ):
        mock_bda = MagicMock()
        mock_bda.invoke_data_automation_async.return_value = {"invocationArn": bda_invocation_arn}
        mock_get_bda_client.return_value = mock_bda

        mock_get_file_bytes.return_value = b"file_content"
        mock_get_page_count.return_value = 3

        result = bda_invoker_util.invoke_bedrock_data_automation(
            "test-bucket", "test.pdf", "test-tenant-id", "test.pdf"
        )

        invocation_arn, project_arn, pages_sent, _ = result
        assert invocation_arn == bda_invocation_arn
        assert project_arn == "arn:aws:project"
        assert pages_sent == 3
        mock_bda.invoke_data_automation_async.assert_called_once()


def test_invoke_bedrock_data_automation_document_truncation():
    bda_invocation_arn = "arn:aws:invocation:123"

    with (
        patch.object(bda_invoker_util, "_project_arns_cache", None),
        patch(
            "documentai_api.utils.bda_invoker.AWSClientFactory.get_bda_runtime_client"
        ) as mock_get_bda_client,
        patch("documentai_api.services.s3.get_file_bytes") as mock_get_file_bytes,
        patch("documentai_api.services.s3.put_object") as mock_put_object,
        patch(
            "documentai_api.utils.bda_invoker.document_utils.get_page_count"
        ) as mock_get_page_count,
        patch("documentai_api.utils.bda_invoker.document_utils.truncate_to_pages") as mock_truncate,
    ):
        mock_bda = MagicMock()
        mock_bda.invoke_data_automation_async.return_value = {"invocationArn": bda_invocation_arn}
        mock_get_bda_client.return_value = mock_bda

        mock_get_file_bytes.return_value = b"file_content"
        mock_get_page_count.return_value = 10
        mock_truncate.return_value = b"truncated_content"

        result = bda_invoker_util.invoke_bedrock_data_automation(
            "test-bucket", "test.pdf", "test-tenant-id", "test.pdf"
        )

        invocation_arn, project_arn, pages_sent, _ = result
        assert invocation_arn == bda_invocation_arn
        assert project_arn == "arn:aws:project"
        assert pages_sent == int(ConfigDefaults.MAX_PAGES_PER_DOCUMENT)
        mock_truncate.assert_called_once_with(
            b"file_content", max_pages=int(ConfigDefaults.MAX_PAGES_PER_DOCUMENT)
        )
        mock_put_object.assert_called_once_with(
            bucket="test-bucket", key="test_truncated.pdf", body=b"truncated_content"
        )


def test_demo_upload_output_key_starts_with_expected_prefix(monkeypatch):
    """Lock the cross-system contract: BDA output for demo uploads.

    BDA output is written to {DOCUMENTAI_OUTPUT_LOCATION}/{tenant_id}/{ddb_key}/{ExtractMethod.BDA}.
    Demo tenant IDs always start with 'demo-' (see demo.py _resolve_demo_context).
    The infra S3 lifecycle rule (expire-demo-results) filters on prefix 'processed/demo-'.

    If this test fails, the lifecycle rule will stop matching and demo output won't auto-expire.
    """
    bda_invocation_arn = "arn:aws:invocation:demo-test"
    demo_source_object = "input/demo/test-tenant-id/doc-uuid.pdf"
    demo_ddb_key = "doc-uuid.pdf"
    tenant_id = "demo-test-sub"

    monkeypatch.setenv(EnvVarNames.DOCUMENTAI_OUTPUT_LOCATION, "s3://output-bucket/processed")
    get_env_config.cache_clear()

    with (
        patch.object(bda_invoker_util, "_project_arns_cache", None),
        patch(
            "documentai_api.utils.bda_invoker.AWSClientFactory.get_bda_runtime_client"
        ) as mock_get_bda_client,
        patch("documentai_api.services.s3.get_file_bytes") as mock_get_file_bytes,
        patch(
            "documentai_api.utils.bda_invoker.document_utils.get_page_count"
        ) as mock_get_page_count,
    ):
        mock_bda = MagicMock()
        mock_bda.invoke_data_automation_async.return_value = {"invocationArn": bda_invocation_arn}
        mock_get_bda_client.return_value = mock_bda

        mock_get_file_bytes.return_value = b"file_content"
        mock_get_page_count.return_value = 1

        bda_invoker_util.invoke_bedrock_data_automation(
            "input-bucket", demo_source_object, tenant_id=tenant_id, ddb_key=demo_ddb_key
        )

        call_kwargs = mock_bda.invoke_data_automation_async.call_args.kwargs
        output_s3_uri = call_kwargs["outputConfiguration"]["s3Uri"]
        output_key = output_s3_uri.replace("s3://output-bucket/", "")
        assert output_key.startswith("processed/demo-"), (
            f"Demo output key '{output_key}' does not start with 'processed/demo-'. "
            "This means the infra S3 lifecycle rule (expire-demo-results) won't match."
        )


@pytest.mark.parametrize(
    ("page_count_return", "expected_pages_sent"),
    [
        (None, 1),
        (0, 1),
    ],
)
def test_invoke_bedrock_data_automation_pages_sent_fallback(page_count_return, expected_pages_sent):
    """When get_page_count returns None or 0, pages_sent defaults to 1."""
    bda_invocation_arn = "arn:aws:invocation:fallback"

    with (
        patch.object(bda_invoker_util, "_project_arns_cache", None),
        patch(
            "documentai_api.utils.bda_invoker.AWSClientFactory.get_bda_runtime_client"
        ) as mock_get_bda_client,
        patch("documentai_api.services.s3.get_file_bytes") as mock_get_file_bytes,
        patch(
            "documentai_api.utils.bda_invoker.document_utils.get_page_count"
        ) as mock_get_page_count,
    ):
        mock_bda = MagicMock()
        mock_bda.invoke_data_automation_async.return_value = {"invocationArn": bda_invocation_arn}
        mock_get_bda_client.return_value = mock_bda

        mock_get_file_bytes.return_value = b"file_content"
        mock_get_page_count.return_value = page_count_return

        _, _, pages_sent, _ = bda_invoker_util.invoke_bedrock_data_automation(
            "test-bucket", "test.pdf", "test-tenant-id", "test.pdf"
        )

        assert pages_sent == expected_pages_sent


# =============================================================================
# skip_bda_if_unclassified tests
# =============================================================================


def test_skip_bda_if_unclassified_defaults_false_when_no_param(monkeypatch):
    """When no SSM prefix is configured, defaults to False (don't skip BDA)."""
    monkeypatch.setattr("os.environ", {})
    get_env_config.cache_clear()
    result = bda_invoker_util.skip_bda_if_unclassified()
    assert result is False


def test_skip_bda_if_unclassified_reads_ssm_true(monkeypatch):
    """When SSM param returns 'true', returns True (skip BDA)."""
    monkeypatch.setenv(EnvVarNames.SSM_PREFIX, "/test")
    get_env_config.cache_clear()
    with patch("documentai_api.utils.ssm.get_parameter_value", return_value="true"):
        result = bda_invoker_util.skip_bda_if_unclassified()
    assert result is True


def test_skip_bda_if_unclassified_reads_ssm_false(monkeypatch):
    """When SSM param returns 'false', returns False (don't skip BDA)."""
    monkeypatch.setenv(EnvVarNames.SSM_PREFIX, "/test")
    get_env_config.cache_clear()
    with patch("documentai_api.utils.ssm.get_parameter_value", return_value="false"):
        result = bda_invoker_util.skip_bda_if_unclassified()
    assert result is False


# =============================================================================
# resolve_project_arn tests
# =============================================================================


def test_resolve_project_arn_returns_category_arn_when_matched():
    """Returns category-specific ARN when the category has a configured project."""
    prefix = "arn:aws:bedrock:us-east-1:123:data-automation-project"
    with (
        patch.object(bda_invoker_util, "_project_arns_cache", None),
        patch("documentai_api.utils.bda_invoker.get_env_config") as mock_config,
    ):
        mock_config.return_value.get_bda_project_arns.return_value = {
            "employer_income": f"{prefix}/emp-arn",
        }
        result, used_category = bda_invoker_util.resolve_project_arn("employer_income")
        assert result == f"{prefix}/emp-arn"
        assert used_category is True


def test_resolve_project_arn_raises_when_category_not_configured():
    """Raises when a matched category has no configured project ARN (deploy misconfig)."""
    prefix = "arn:aws:bedrock:us-east-1:123:data-automation-project"
    with (
        patch.object(bda_invoker_util, "_project_arns_cache", None),
        patch("documentai_api.utils.bda_invoker.get_env_config") as mock_config,
    ):
        mock_config.return_value.get_bda_project_arns.return_value = {
            "employer_income": f"{prefix}/emp-arn",
        }
        with pytest.raises(ValueError, match="employer_expenses"):
            bda_invoker_util.resolve_project_arn("employer_expenses")


def test_resolve_project_arn_falls_back_to_default_when_no_category():
    """Falls back to the default project (bda_project_arn) when category is None.

    Blueprint matching legitimately yields no category for valid documents (low
    confidence, "OTHER", the flag disabled, or a model error) - this is not a
    misconfiguration.
    """
    prefix = "arn:aws:bedrock:us-east-1:123:data-automation-project"
    with (
        patch.object(bda_invoker_util, "_project_arns_cache", None),
        patch("documentai_api.utils.bda_invoker.get_env_config") as mock_config,
    ):
        mock_config.return_value.get_bda_project_arns.return_value = {
            "employer_income": f"{prefix}/emp-arn",
        }
        mock_config.return_value.bda_project_arn = f"{prefix}/default-arn"
        result, used_category = bda_invoker_util.resolve_project_arn(None)
        assert result == f"{prefix}/default-arn"
        assert used_category is False


def test_resolve_project_arn_raises_when_no_category_and_no_default_configured():
    """Raises when category is None and no default project (bda_project_arn) is configured."""
    prefix = "arn:aws:bedrock:us-east-1:123:data-automation-project"
    with (
        patch.object(bda_invoker_util, "_project_arns_cache", None),
        patch("documentai_api.utils.bda_invoker.get_env_config") as mock_config,
    ):
        mock_config.return_value.get_bda_project_arns.return_value = {
            "employer_income": f"{prefix}/emp-arn",
        }
        mock_config.return_value.bda_project_arn = None
        with pytest.raises(ValueError, match="No preclassification category matched"):
            bda_invoker_util.resolve_project_arn(None)
