from typing import Any
from urllib.parse import urlparse

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
    """Extract file key and bucket name from EventBridge event."""
    try:
        file_key = event["detail"]["object"]["key"]
        bucket_name = event["detail"]["bucket"]["name"]

        if include_metadata:
            metadata_response = s3_service.head_object(bucket_name, file_key)
            metadata = metadata_response.get("Metadata", {})
            return file_key, bucket_name, metadata

        return file_key, bucket_name
    except (KeyError, TypeError):
        raise ValueError("Invalid EventBridge event structure") from None
