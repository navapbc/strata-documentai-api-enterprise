"""Wire contract test for services/bedrock.py using botocore Stubber.

Verifies the exact request shape sent to Bedrock Converse API.
"""

import boto3
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from documentai_api.services.bedrock import invoke_model


def test_converse_request_shape(monkeypatch):
    """Verify invoke_model sends correct request to Converse API."""
    client = boto3.client("bedrock-runtime", region_name="us-east-1")
    stubber = Stubber(client)

    # Expected request parameters
    expected_params = {
        "modelId": "us.amazon.nova-lite-v1:0",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"image": {"format": "png", "source": {"bytes": b"\x89PNG"}}},
                    {"text": "classify this"},
                ],
            }
        ],
        "inferenceConfig": {"maxTokens": 256},
    }

    # Stubbed response matching Converse API shape
    stubbed_response = {
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "text": '{"document_type": "tax_documents", "confidence": 0.95, "document_count": 1, "is_document": true}'
                    }
                ],
            }
        },
        "stopReason": "end_turn",
        "usage": {"inputTokens": 100, "outputTokens": 50, "totalTokens": 150},
        "metrics": {"latencyMs": 500},
    }

    stubber.add_response("converse", stubbed_response, expected_params)

    # Patch the client factory to return our stubbed client
    monkeypatch.setattr(
        "documentai_api.utils.aws_client_factory.AWSClientFactory.get_bedrock_runtime_client",
        lambda: client,
    )

    with stubber:
        messages = [
            {
                "role": "user",
                "content": [
                    {"image": {"format": "png", "source": {"bytes": b"\x89PNG"}}},
                    {"text": "classify this"},
                ],
            }
        ]

        result = invoke_model(
            model_id="us.amazon.nova-lite-v1:0",
            messages=messages,
            max_tokens=256,
        )

    # Verify response is parsed correctly
    assert result["role"] == "assistant"
    assert (
        result["content"][0]["text"]
        == '{"document_type": "tax_documents", "confidence": 0.95, "document_count": 1, "is_document": true}'
    )

    # Stubber verifies the request matched expected_params - if not, it raises
    stubber.assert_no_pending_responses()


def test_retries_on_throttling(monkeypatch):
    """Verify invoke_model retries on ThrottlingException."""
    client = boto3.client("bedrock-runtime", region_name="us-east-1")
    stubber = Stubber(client)

    monkeypatch.setattr(
        "documentai_api.utils.aws_client_factory.AWSClientFactory.get_bedrock_runtime_client",
        lambda: client,
    )

    # First call: throttled
    stubber.add_client_error("converse", "ThrottlingException", "Rate exceeded")

    # Second call: success
    stubber.add_response(
        "converse",
        {
            "output": {"message": {"role": "assistant", "content": [{"text": "{}"}]}},
            "stopReason": "end_turn",
            "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
            "metrics": {"latencyMs": 100},
        },
    )

    messages = [{"role": "user", "content": [{"text": "test"}]}]

    with stubber:
        result = invoke_model(model_id="test-model", messages=messages)

    assert result["role"] == "assistant"
    stubber.assert_no_pending_responses()


def test_does_not_retry_non_retryable_error(monkeypatch):
    """Non-retryable ClientErrors are raised immediately."""
    client = boto3.client("bedrock-runtime", region_name="us-east-1")
    stubber = Stubber(client)

    monkeypatch.setattr(
        "documentai_api.utils.aws_client_factory.AWSClientFactory.get_bedrock_runtime_client",
        lambda: client,
    )

    stubber.add_client_error("converse", "ValidationException", "Bad request")

    messages = [{"role": "user", "content": [{"text": "test"}]}]

    import pytest

    with stubber, pytest.raises(ClientError) as exc_info:
        invoke_model(model_id="test-model", messages=messages)

    assert exc_info.value.response["Error"]["Code"] == "ValidationException"
