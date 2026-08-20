"""Tests for services/bda.py."""

import json

import pytest

from documentai_api.config.env import EnvVars
from documentai_api.services import bda as bda_service

PROJECT_ARN_ALL = "arn:aws:bedrock:us-east-1:123:project/all"
PROJECT_ARN_INCOME = "arn:aws:bedrock:us-east-1:123:project/income"
PROFILE_ARN = "arn:aws:bedrock:us-east-1:123:profile/default"
INVOCATION_ARN = "arn:aws:bedrock:us-east-1:123:invocation/abc"

PROJECT_ARNS_MAP = json.dumps(
    {
        "income": PROJECT_ARN_INCOME,
        "expenses": "arn:aws:bedrock:us-east-1:123:project/expenses",
    }
)


# =============================================================================
# get_data_automation_project / get_blueprint
# =============================================================================


def test_get_data_automation_project(mock_bda_client):
    project_arn = "arn:aws:bedrock:us-east-1:123:project/test"
    mock_bda_client.get_data_automation_project.return_value = {"projectArn": project_arn}

    result = bda_service.get_data_automation_project(project_arn)

    assert result["projectArn"] == project_arn
    mock_bda_client.get_data_automation_project.assert_called_once_with(projectArn=project_arn)


def test_get_blueprint(mock_bda_client):
    blueprint_arn = "arn:aws:bedrock:us-east-1:123:blueprint/test"
    mock_bda_client.get_blueprint.return_value = {"blueprintArn": blueprint_arn}

    result = bda_service.get_blueprint(blueprint_arn)

    assert result["blueprintArn"] == blueprint_arn
    mock_bda_client.get_blueprint.assert_called_once_with(blueprintArn=blueprint_arn)


# =============================================================================
# get_project_arn_for_category
# =============================================================================


def test_get_project_arn_uses_map_when_set(monkeypatch):
    monkeypatch.setenv(EnvVars.BDA_PROJECT_ARNS, PROJECT_ARNS_MAP)
    assert bda_service.get_project_arn_for_category("income") == PROJECT_ARN_INCOME


def test_get_project_arn_raises_for_unknown_category(monkeypatch):
    monkeypatch.setenv(EnvVars.BDA_PROJECT_ARNS, PROJECT_ARNS_MAP)
    with pytest.raises(ValueError, match="Unknown document category"):
        bda_service.get_project_arn_for_category("unknown")


def test_get_project_arn_falls_back_to_all_when_no_map(monkeypatch):
    monkeypatch.setenv(EnvVars.BDA_PROJECT_ARN_ALL, PROJECT_ARN_ALL)
    assert bda_service.get_project_arn_for_category("anything") == PROJECT_ARN_ALL


def test_get_project_arn_raises_when_no_map_and_no_fallback():
    with pytest.raises(ValueError, match="BDA_PROJECT_ARN_ALL"):
        bda_service.get_project_arn_for_category("income")


# =============================================================================
# invoke_bda_async
# =============================================================================


def test_invoke_bda_async_returns_invocation_arn(monkeypatch, mock_bda_runtime_client):
    monkeypatch.setenv(EnvVars.BDA_PROJECT_ARNS, PROJECT_ARNS_MAP)
    monkeypatch.setenv(EnvVars.BDA_PROFILE_ARN, PROFILE_ARN)
    mock_bda_runtime_client.invoke_data_automation_async.return_value = {
        "invocationArn": INVOCATION_ARN
    }

    result = bda_service.invoke_bda_async(
        input_s3_uri="s3://input-bucket/test.pdf",
        output_s3_uri="s3://output-bucket/test.pdf",
        document_category="income",
    )

    assert result == INVOCATION_ARN


def test_invoke_bda_async_passes_correct_args(monkeypatch, mock_bda_runtime_client):
    monkeypatch.setenv(EnvVars.BDA_PROJECT_ARNS, PROJECT_ARNS_MAP)
    monkeypatch.setenv(EnvVars.BDA_PROFILE_ARN, PROFILE_ARN)
    mock_bda_runtime_client.invoke_data_automation_async.return_value = {
        "invocationArn": INVOCATION_ARN
    }

    bda_service.invoke_bda_async(
        input_s3_uri="s3://input-bucket/test.pdf",
        output_s3_uri="s3://output-bucket/test.pdf",
        document_category="income",
    )

    mock_bda_runtime_client.invoke_data_automation_async.assert_called_once_with(
        dataAutomationProfileArn=PROFILE_ARN,
        dataAutomationConfiguration={"dataAutomationProjectArn": PROJECT_ARN_INCOME},
        inputConfiguration={"s3Uri": "s3://input-bucket/test.pdf"},
        outputConfiguration={"s3Uri": "s3://output-bucket/test.pdf"},
    )


def test_invoke_bda_async_raises_for_unknown_category(monkeypatch, mock_bda_runtime_client):
    monkeypatch.setenv(EnvVars.BDA_PROJECT_ARNS, PROJECT_ARNS_MAP)
    monkeypatch.setenv(EnvVars.BDA_PROFILE_ARN, PROFILE_ARN)

    with pytest.raises(ValueError, match="Unknown document category"):
        bda_service.invoke_bda_async(
            input_s3_uri="s3://input-bucket/test.pdf",
            output_s3_uri="s3://output-bucket/test.pdf",
            document_category="unknown",
        )


# =============================================================================
# get_bda_job_response
# =============================================================================


def test_get_bda_job_response_success(mock_bda_runtime_client):
    mock_bda_runtime_client.get_data_automation_status.return_value = {"status": "InProgress"}

    result = bda_service.get_bda_job_response("arn:aws:bedrock:us-east-1:123:invocation/test")

    assert result["status"] == "InProgress"


def test_get_bda_job_response_exception(mock_bda_runtime_client):
    mock_bda_runtime_client.get_data_automation_status.side_effect = Exception("API error")

    result = bda_service.get_bda_job_response("arn:aws:bedrock:us-east-1:123:invocation/test")

    assert result is None


# =============================================================================
# get_bda_result_json
# =============================================================================


def test_get_bda_result_json_success(s3_bucket, monkeypatch):
    from documentai_api.config.env import get_aws_config

    monkeypatch.setenv("DOCUMENTAI_OUTPUT_LOCATION", f"s3://{s3_bucket.name}/output")
    get_aws_config.cache_clear()
    s3_bucket.put_object(Key="path/to/result.json", Body=b'{"result": "success"}')

    result = bda_service.get_bda_result_json(f"s3://{s3_bucket.name}/path/to/result.json")

    assert result == {"result": "success"}


def test_get_bda_result_json_empty_uri():
    assert bda_service.get_bda_result_json("") is None


def test_get_bda_result_json_exception(aws_credentials):
    assert bda_service.get_bda_result_json("s3://nonexistent-bucket/key") is None


@pytest.mark.parametrize(
    "body",
    [
        b'["not", "an", "object"]',
        b"{not valid json",
    ],
)
def test_get_bda_result_json_returns_none_for_invalid_body(s3_bucket, body):
    s3_bucket.put_object(Key="path/to/result.json", Body=body)

    assert bda_service.get_bda_result_json(f"s3://{s3_bucket.name}/path/to/result.json") is None


# =============================================================================
# extract_bda_output_s3_uri
# =============================================================================


def test_extract_bda_output_s3_uri_custom_path(s3_bucket):
    s3_bucket.put_object(
        Key="metadata.json",
        Body=f'{{"output_metadata": [{{"segment_metadata": [{{"custom_output_path": "s3://{s3_bucket.name}/custom/output.json"}}]}}]}}'.encode(),
    )

    result = bda_service.extract_bda_output_s3_uri(s3_bucket.name, "metadata.json")

    assert result == f"s3://{s3_bucket.name}/custom/output.json"


def test_extract_bda_output_s3_uri_standard_path(s3_bucket):
    s3_bucket.put_object(
        Key="metadata.json",
        Body=f'{{"output_metadata": [{{"segment_metadata": [{{"standard_output_path": "s3://{s3_bucket.name}/standard/output.json"}}]}}]}}'.encode(),
    )

    result = bda_service.extract_bda_output_s3_uri(s3_bucket.name, "metadata.json")

    assert result == f"s3://{s3_bucket.name}/standard/output.json"


@pytest.mark.parametrize(
    "body",
    [
        b'{"output_metadata": []}',
        b"[1, 2, 3]",
        b"{not valid json",
        b'{"output_metadata": "not a list"}',
    ],
)
def test_extract_bda_output_s3_uri_returns_none_for_invalid_body(s3_bucket, body):
    s3_bucket.put_object(Key="metadata.json", Body=body)

    assert bda_service.extract_bda_output_s3_uri(s3_bucket.name, "metadata.json") is None
