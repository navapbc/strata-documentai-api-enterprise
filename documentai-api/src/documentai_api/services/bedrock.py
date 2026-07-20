from __future__ import annotations

from typing import TYPE_CHECKING, Any

from botocore.exceptions import ClientError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from documentai_api.utils.aws_client_factory import AWSClientFactory

if TYPE_CHECKING:
    from mypy_boto3_bedrock_runtime.type_defs import InferenceConfigurationTypeDef

RETRYABLE_ERROR_CODES = ("ThrottlingException", "ServiceUnavailableException")


def _is_retryable_client_error(exc: BaseException) -> bool:
    return isinstance(exc, ClientError) and exc.response["Error"]["Code"] in RETRYABLE_ERROR_CODES


@retry(
    retry=retry_if_exception(_is_retryable_client_error),
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=10),
)
def invoke_model(
    model_id: str, messages: list[Any], max_tokens: int = 256, temperature: float | None = None
) -> Any:
    client = AWSClientFactory.get_bedrock_runtime_client()
    inference_config: InferenceConfigurationTypeDef = {"maxTokens": max_tokens}
    if temperature is not None:
        inference_config["temperature"] = temperature
    response = client.converse(
        modelId=model_id,
        messages=messages,
        inferenceConfig=inference_config,
    )
    return response
