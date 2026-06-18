"""S3 Service methods."""

from __future__ import annotations

from datetime import datetime
from typing import IO, TYPE_CHECKING, Any

from botocore.config import Config

from documentai_api.config.constants import ConfigDefaults
from documentai_api.utils.aws_client_factory import AWSClientFactory

_PRESIGN_CONFIG = Config(signature_version=ConfigDefaults.PRESIGNED_URL_SIGNATURE_VERSION)

if TYPE_CHECKING:
    from mypy_boto3_s3.type_defs import (
        GetObjectOutputTypeDef,
        HeadObjectOutputTypeDef,
        ObjectIdentifierTypeDef,
    )


def upload_file(
    bucket: str,
    key: str,
    file_obj: IO[bytes],
    content_type: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Upload file to S3."""
    s3_client = AWSClientFactory.get_s3_client()

    extra_args: dict[str, str | dict[str, str]] = {}

    if content_type:
        extra_args["ContentType"] = content_type

    if metadata:
        extra_args["Metadata"] = metadata

    s3_client.upload_fileobj(file_obj, bucket, key, ExtraArgs=extra_args)


def get_object(bucket: str, key: str) -> GetObjectOutputTypeDef:
    """Get object from S3."""
    s3_client = AWSClientFactory.get_s3_client()
    return s3_client.get_object(Bucket=bucket, Key=key)


def head_object(bucket: str, key: str) -> HeadObjectOutputTypeDef:
    """Get object metadata from S3."""
    s3_client = AWSClientFactory.get_s3_client()
    return s3_client.head_object(Bucket=bucket, Key=key)


def put_object(bucket: str, key: str, body: bytes, content_type: str | None = None) -> None:
    """Put object to S3."""
    s3_client = AWSClientFactory.get_s3_client()

    if content_type:
        s3_client.put_object(Bucket=bucket, Key=key, Body=body, ContentType=content_type)
    else:
        s3_client.put_object(Bucket=bucket, Key=key, Body=body)


def delete_object(bucket: str, key: str) -> None:
    """Delete file from S3."""
    s3_client = AWSClientFactory.get_s3_client()
    s3_client.delete_object(Bucket=bucket, Key=key)


def delete_prefix(bucket: str, prefix: str) -> int:
    """Delete every object under a prefix. Returns the number of objects deleted."""
    s3_client = AWSClientFactory.get_s3_client()
    paginator = s3_client.get_paginator("list_objects_v2")

    deleted = 0
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        objects: list[ObjectIdentifierTypeDef] = [
            {"Key": obj["Key"]} for obj in page.get("Contents", [])
        ]
        if objects:
            s3_client.delete_objects(Bucket=bucket, Delete={"Objects": objects})
            deleted += len(objects)
    return deleted


def get_content_type(bucket: str, key: str) -> str:
    """Get file content type."""
    response = head_object(bucket, key)
    return str(response.get("ContentType", "application/octet-stream"))


def get_file_size_bytes(bucket: str, key: str) -> int:
    """Get file size in bytes."""
    response = head_object(bucket, key)
    return int(response.get("ContentLength", 0))


def get_file_bytes(bucket: str, key: str) -> bytes:
    """Get file content as bytes."""
    response = get_object(bucket, key)
    return bytes(response["Body"].read())


def is_password_protected(bucket: str, key: str) -> bool:
    """Check if PDF is password protected."""
    content_type = get_content_type(bucket, key)

    if content_type in ["application/pdf", "binary/octet-stream"]:
        file_bytes = get_file_bytes(bucket, key)
        return b"/Encrypt" in file_bytes[:2048]

    return False


def get_last_modified_at(bucket: str, key: str) -> datetime:
    """Get object's last modified timestamp."""
    response = head_object(bucket, key)
    return response["LastModified"]


def generate_presigned_get_url(
    bucket: str,
    key: str,
    expiration: int = 300,
    content_type: str | None = None,
) -> str:
    """Generate a presigned GET URL for downloading/viewing an S3 object.

    Args:
        bucket: S3 bucket name
        key: S3 object key
        expiration: URL expiration time in seconds (default: 5 minutes)
        content_type: If set, overrides Content-Type via response-content-type

    Returns:
        Presigned URL string.
    """
    s3_client = AWSClientFactory.get_session().client(
        "s3",
        region_name=AWSClientFactory.get_region(),
        config=_PRESIGN_CONFIG,
    )

    params: dict[str, Any] = {"Bucket": bucket, "Key": key}
    if content_type:
        params["ResponseContentType"] = content_type
        params["ResponseContentDisposition"] = "inline"

    return s3_client.generate_presigned_url(
        "get_object",
        Params=params,
        ExpiresIn=expiration,
    )


def generate_presigned_post(
    bucket: str,
    key: str,
    content_type: str,
    max_size_bytes: int,
    metadata: dict[str, str] | None = None,
    expiration: int = 900,
) -> dict[str, Any]:
    """Generate a presigned POST for browser/mobile-direct uploads.

    Unlike presigned PUT URLs, POST policies enforce size and content-type
    at S3 - the upload is rejected before bytes land if conditions aren't met.

    Args:
        bucket: S3 bucket name
        key: S3 object key
        content_type: Required content type for the upload
        max_size_bytes: Maximum allowed upload size in bytes
        metadata: S3 user metadata to attach to the object
        expiration: Policy expiration time in seconds (default: 15 minutes)

    Returns:
        Dict with 'url' and 'fields' for the client to POST.
    """
    s3_client = AWSClientFactory.get_s3_client()

    fields: dict[str, str] = {"Content-Type": content_type}
    conditions: list[Any] = [
        {"Content-Type": content_type},
        ["content-length-range", 1, max_size_bytes],
    ]

    if metadata:
        for k, v in metadata.items():
            meta_key = f"x-amz-meta-{k}"
            fields[meta_key] = v
            conditions.append({meta_key: v})

    return s3_client.generate_presigned_post(
        Bucket=bucket,
        Key=key,
        Fields=fields,
        Conditions=conditions,
        ExpiresIn=expiration,
    )
