from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from documentai_api.services.aws_client_factory import AWSClientFactory
from documentai_api.services.exceptions import is_retryable

if TYPE_CHECKING:
    from mypy_boto3_bedrock_runtime.type_defs import InferenceConfigurationTypeDef


@retry(
    retry=retry_if_exception(is_retryable),
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=10),
)
def invoke_model(
    model_id: str,
    messages: list[Any],
    max_tokens: int = 256,
    temperature: float | None = None,
    system: list[Any] | None = None,
) -> Any:
    client = AWSClientFactory.get_bedrock_runtime_client()
    inference_config: InferenceConfigurationTypeDef = {"maxTokens": max_tokens}
    if temperature is not None:
        inference_config["temperature"] = temperature

    kwargs: dict[str, Any] = {
        "modelId": model_id,
        "messages": messages,
        "inferenceConfig": inference_config,
    }

    if system is not None:
        kwargs["system"] = system
    response = client.converse(**kwargs)

    return response
