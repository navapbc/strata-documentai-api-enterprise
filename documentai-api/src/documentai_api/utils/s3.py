from typing import Any
from urllib.parse import unquote_plus, urlparse

from documentai_api.services import s3 as s3_service


def parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    """Parse S3 URI into bucket and key.

    Args:
        s3_uri: S3 URI in format s3://bucket/key

    Returns:
        Tuple of (bucket, key)
    """
    parts = urlparse(s3_uri)
    bucket_name = parts.netloc
    prefix = parts.path.lstrip("/")
    return (bucket_name, prefix)


def get_s3_prefix_from_location(s3_location: str) -> str:
    """Extract S3 prefix from location environment variable.

    Args:
        s3_location: Environment variable value (e.g. "s3://bucket/input")

    Returns:
        The prefix portion (e.g. "input"), or empty string if no prefix
    """
    if not s3_location:
        return ""

    _, prefix = parse_s3_uri(s3_location)
    return prefix


def extract_s3_info_from_event(
    event: dict[str, Any], include_metadata: bool = False
) -> tuple[str, str] | tuple[str, str, dict[str, str]]:
    """Extract file key and bucket name from an S3 event.

    Supports both event shapes a Lambda can receive when triggered by S3:

    - **EventBridge S3 event** (S3 -> EventBridge rule -> Lambda):
      ``event["detail"]["object"]["key"]`` and
      ``event["detail"]["bucket"]["name"]``
    - **Direct S3 notification** (S3 -> Lambda invocation):
      ``event["Records"][0]["s3"]["object"]["key"]`` and
      ``event["Records"][0]["s3"]["bucket"]["name"]``

    In both shapes the key is URL-encoded by S3 (spaces become ``+``,
    other special characters become ``%XX``). The returned key is decoded.

    Args:
        event: S3 event from either trigger style.
        include_metadata: If True, also fetch and return the S3 object's user metadata.

    Returns:
        (file_key, bucket_name) or (file_key, bucket_name, metadata).

    Raises:
        ValueError: If the event matches neither supported shape.
    """
    try:
        if "detail" in event:
            file_key = event["detail"]["object"]["key"]
            bucket_name = event["detail"]["bucket"]["name"]
        elif "Records" in event:
            record = event["Records"][0]
            file_key = record["s3"]["object"]["key"]
            bucket_name = record["s3"]["bucket"]["name"]
        else:
            raise ValueError(
                "Invalid S3 event structure: expected 'detail' (EventBridge) "
                "or 'Records' (direct S3 notification)"
            )
    except (KeyError, TypeError, IndexError) as e:
        raise ValueError(f"Invalid S3 event structure: {e}") from None

    file_key = unquote_plus(file_key)

    if include_metadata:
        metadata_response = s3_service.head_object(bucket_name, file_key)
        metadata = metadata_response.get("Metadata", {})
        return file_key, bucket_name, metadata

    return file_key, bucket_name
