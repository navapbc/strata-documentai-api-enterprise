from typing import Any

from botocore.exceptions import ClientError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from documentai_api.utils.aws_client_factory import AWSClientFactory

RETRYABLE_ERROR_CODES = ("ThrottlingException", "ServiceUnavailableException")


def _is_retryable_client_error(exc: BaseException) -> bool:
    return isinstance(exc, ClientError) and exc.response["Error"]["Code"] in RETRYABLE_ERROR_CODES


@retry(
    retry=retry_if_exception(_is_retryable_client_error),
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=10),
)
def invoke_model(model_id: str, messages: list[Any], max_tokens: int = 256) -> Any:
    client = AWSClientFactory.get_bedrock_runtime_client()
    response = client.converse(
        modelId=model_id,
        messages=messages,
        inferenceConfig={"maxTokens": max_tokens},
    )
    return response
