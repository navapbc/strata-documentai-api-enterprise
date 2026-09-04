from botocore.exceptions import ClientError

_RETRYABLE_ERROR_CODES = ("ThrottlingException", "ServiceUnavailableException")


def is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, ClientError) and exc.response["Error"]["Code"] in _RETRYABLE_ERROR_CODES
