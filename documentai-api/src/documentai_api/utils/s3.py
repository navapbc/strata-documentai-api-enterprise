import json
import os
from typing import Any
from urllib.parse import quote, unquote_plus

from botocore.exceptions import ClientError
from fastapi import HTTPException

from documentai_api.config.env import get_env_config
from documentai_api.constants.processing import ExtractMethod
from documentai_api.services import s3 as s3_service
from documentai_api.utils.cache import get_cache


def parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    """Parse S3 URI into bucket and key.

    Args:
        s3_uri: S3 URI in format s3://bucket/key

    Returns:
        Tuple of (bucket, key)
    """
    if not s3_uri.startswith("s3://"):
        raise ValueError(f"Invalid S3 URI: {s3_uri}")

    bucket_name, _, prefix = s3_uri.removeprefix("s3://").partition("/")
    return (bucket_name, prefix)


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


def build_s3_key(*parts: str) -> str:
    """Build an S3 object key from path segments, normalizing slashes.

    Strips leading/trailing slashes from each part and joins with '/'.
    Empty parts are skipped.
    """
    return "/".join(p.strip("/") for p in parts if p)


def generate_s3_uri(
    location_uri: str, tenant_id: str, ddb_key: str, extraction_method: ExtractMethod
) -> str:
    """Return a fully-qualified S3 URI for a tenant-scoped extraction artifact."""
    bucket, key = get_bucket_and_key(location_uri, tenant_id, f"{ddb_key}/{extraction_method}")
    return f"s3://{bucket}/{key}"


def get_bucket_and_key(location_uri: str, tenant_id: str | None, file_name: str) -> tuple[str, str]:
    """Resolve (bucket, key) for a tenant-scoped document artifact.

    Encodes the storage layout in one place - ``{prefix}/{tenant}/{file_name}``
    - so the upload/processing writers and the delete path can't drift on how a
    document's S3 objects are keyed. When ``tenant_id`` is falsy the tenant
    segment is omitted (legacy un-scoped paths, e.g. document builds); empty
    segments are skipped.
    """
    bucket, prefix = parse_s3_uri(location_uri)
    return bucket, build_s3_key(prefix, tenant_id or "", file_name)


def write_extraction_output(
    tenant_id: str,
    extraction_method: str,
    file_name: str,
    body: bytes,
    content_type: str | None = None,
) -> str:
    """Write a tenant-scoped extraction artifact to S3 and return its URI.

    Enforces the ``{prefix}/{tenant_id}/{file_name}/{extraction_method}`` key
    convention so callers never construct output keys manually.
    """
    if not tenant_id:
        raise ValueError("tenant_id is required for extraction output")

    output_location = get_env_config().output_location
    bucket, key = get_bucket_and_key(
        output_location, tenant_id, f"{file_name}/{extraction_method}/result.json"
    )
    s3_service.put_object(bucket, key, body, content_type)
    return f"s3://{bucket}/{key}"


def get_truncated_object_key(object_key: str) -> str:
    """Return the key used for the truncated copy of an oversized document.

    bda_invoker writes a truncated copy back to the input bucket when a document
    exceeds MAX_PAGES_PER_DOCUMENT. This helper centralises the naming convention
    so the invoker and the hard-delete purge can't drift apart.
    """
    base, ext = os.path.splitext(object_key)
    return f"{base}_truncated{ext}"


def read_json_from_s3(s3_uri: str) -> Any:
    """Fetch and JSON-decode an S3 object by URI."""
    bucket, key = parse_s3_uri(s3_uri)
    body = s3_service.get_object(bucket, key)["Body"].read()
    return json.loads(body)


def get_lifecycle_expiration_days(bucket: str, key: str) -> int | None:
    """Return the expiration days from the most specific matching lifecycle rule for a key.

    Matches rules by prefix (longest prefix wins). The full lifecycle config is
    cached per bucket for 60 minutes so repeated lookups for different keys in
    the same bucket don't each hit S3. On fetch failure, an empty list is cached
    for 5 minutes to avoid hammering S3 (e.g. when the role lacks
    s3:GetLifecycleConfiguration).
    """
    cache = get_cache()
    cache_key = f"lifecycle:{bucket}"
    rules: list[dict[str, Any]] | None = cache.get(cache_key)

    if rules is None:
        try:
            config = s3_service.get_bucket_lifecycle_configuration(bucket)
            rules = [
                {
                    "prefix": _lifecycle_prefix(r),
                    "days": r.get("Expiration", {}).get("Days"),
                }
                for r in config.get("Rules", [])
                if r.get("Status") == "Enabled"
                and r.get("Expiration", {}).get("Days")
                and _lifecycle_prefix(r) is not None
            ]
            cache.add(cache_key, rules, ttl_minutes=60)
        except Exception:
            cache.add(cache_key, [], ttl_minutes=5)
            return None

    rules_sorted = sorted(rules, key=lambda r: len(r["prefix"]), reverse=True)
    for rule in rules_sorted:
        if key.startswith(rule["prefix"]):
            return int(rule["days"])

    return None


def _lifecycle_prefix(rule: dict[str, Any]) -> str | None:
    """Extract the prefix string from a lifecycle rule, or None if the filter shape is unsupported.

    Only simple Prefix filters are supported. Rules using And (tag/size filters)
    are skipped to avoid silently matching the wrong rule.
    """
    f = rule.get("Filter", {})
    if "And" in f:
        return None
    if "Prefix" in f:
        return str(f["Prefix"])
    # Legacy top-level Prefix field (pre-2016 lifecycle API)
    return str(rule.get("Prefix", ""))


def assert_object_exists(bucket: str, key: str) -> None:
    """Check that an S3 object exists, raising HTTPException if not.

    Raises 404 when the object is missing (NoSuchKey or 404 from head_object),
    with a lifecycle-aware message if expiration days can be determined.
    Re-raises ClientError for all other error codes so the caller's outer
    handler can return a 5xx.
    """
    try:
        s3_service.head_object(bucket, key)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            days = get_lifecycle_expiration_days(bucket, key)
            detail = (
                f"Preview file no longer exists - files are purged after {days} days"
                if days
                else "Preview file no longer exists"
            )
            raise HTTPException(status_code=404, detail=detail) from e
        raise


def sanitize_for_s3_metadata(value: str, max_length: int = 512) -> str:
    """Percent-encode non-ASCII and truncate for S3 user metadata.

    S3 user metadata values must be ASCII-only and the total of all
    user metadata is capped at 2 KB.
    """
    return quote(value[:max_length], safe="")


# Disallowed by Bedrock Data Automation's S3 URI validation regex, except
# backslash and backtick (92, 96), which are banned defensively, not by BDA.
_BANNED_ORDINALS = frozenset(
    {
        34,  # "
        35,  # #
        37,  # %
        60,  # <
        62,  # >
        91,  # [
        92,  # \
        93,  # ]
        94,  # ^
        96,  # `
        123,  # {
        124,  # |
        125,  # }
        126,  # ~
    }
)


def sanitize_for_s3_key(value: str) -> str:
    """Replace characters unsafe for S3 object keys with underscores.

    Non-ASCII bytes and control characters break the URL-encoding round-trip
    in S3 event notifications; see the comment above _BANNED_ORDINALS for the rest.
    """
    return "".join(
        "_" if ord(c) > 126 or ord(c) < 32 or ord(c) in _BANNED_ORDINALS else c for c in value
    )
