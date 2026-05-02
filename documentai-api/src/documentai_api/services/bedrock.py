from typing import Any

from documentai_api.utils.aws_client_factory import AWSClientFactory


def invoke_model(model_id: str, messages: list[Any], max_tokens: int = 256) -> Any:
    client = AWSClientFactory.get_bedrock_runtime_client()
    response = client.converse(
        modelId=model_id,
        messages=messages,
        inferenceConfig={"maxTokens": max_tokens},
    )
    return response["output"]["message"]
