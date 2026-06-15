"""Tests for utils/s3.py."""

import pytest

from documentai_api.utils import s3 as s3_util


@pytest.mark.parametrize(
    ("s3_uri", "expected_bucket", "expected_key"),
    [
        ("s3://bucket/key", "bucket", "key"),
        ("s3://my-bucket/path/to/file.json", "my-bucket", "path/to/file.json"),
        ("s3://bucket/prefix/input/file.pdf", "bucket", "prefix/input/file.pdf"),
        ("s3://bucket", "bucket", ""),  # No key
    ],
)
def test_parse_s3_uri(s3_uri, expected_bucket, expected_key):
    """Parse S3 URIs into bucket and key."""
    bucket, key = s3_util.parse_s3_uri(s3_uri)
    assert bucket == expected_bucket
    assert key == expected_key


@pytest.mark.parametrize(
    ("s3_location", "expected_prefix"),
    [
        ("s3://bucket/input", "input"),
        ("s3://bucket/processed", "processed"),
        ("s3://bucket/path/to/files", "path/to/files"),
        ("s3://bucket", ""),  # No prefix
        ("", ""),  # Empty string
    ],
)
def test_get_s3_prefix_from_location(s3_location, expected_prefix):
    """Extract prefix from S3 location."""
    prefix = s3_util.get_s3_prefix_from_location(s3_location)
    assert prefix == expected_prefix


# === extract_s3_info_from_event ===


def test_extract_s3_info_from_eventbridge_event():
    """Parse an EventBridge S3 event."""
    event = {
        "source": "aws.s3",
        "detail-type": "Object Created",
        "detail": {
            "bucket": {"name": "my-bucket"},
            "object": {"key": "input/doc.pdf"},
        },
    }
    key, bucket = s3_util.extract_s3_info_from_event(event)
    assert bucket == "my-bucket"
    assert key == "input/doc.pdf"


def test_extract_s3_info_from_direct_s3_notification():
    """Parse a direct S3 notification event (Records[].s3.*)."""
    event = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": {"name": "my-bucket"},
                    "object": {"key": "input/doc.pdf"},
                },
            }
        ]
    }
    key, bucket = s3_util.extract_s3_info_from_event(event)
    assert bucket == "my-bucket"
    assert key == "input/doc.pdf"


@pytest.mark.parametrize(
    ("raw_key", "expected_key"),
    [
        ("input/hello+world.pdf", "input/hello world.pdf"),
        ("input/file%20with%20spaces.pdf", "input/file with spaces.pdf"),
        ("input/spe%C3%A7ial.pdf", "input/speçial.pdf"),
        ("input/plain.pdf", "input/plain.pdf"),
    ],
)
def test_extract_s3_info_url_decodes_key(raw_key, expected_key):
    """S3 events URL-encode object keys; the returned key should be decoded."""
    event = {
        "detail": {
            "bucket": {"name": "b"},
            "object": {"key": raw_key},
        }
    }
    key, _ = s3_util.extract_s3_info_from_event(event)
    assert key == expected_key


@pytest.mark.parametrize(
    "event",
    [
        {},
        {"unrelated": "shape"},
        {"detail": {"bucket": {"name": "b"}}},  # missing object
        {"detail": {"object": {"key": "k"}}},  # missing bucket
        {"Records": []},  # empty Records
        {"Records": [{"s3": {"bucket": {"name": "b"}}}]},  # missing object
    ],
)
def test_extract_s3_info_raises_on_invalid_shape(event):
    """Malformed events raise ValueError."""
    with pytest.raises(ValueError, match="Invalid S3 event structure"):
        s3_util.extract_s3_info_from_event(event)


@pytest.mark.parametrize(
    ("tenant_id", "expected_key"),
    [
        ("tenant-a", "input/tenant-a/doc.pdf"),
        (None, "input/doc.pdf"),
    ],
)
def test_get_bucket_and_key(tenant_id, expected_key):
    """Layout is centralized: {prefix}/{tenant}/{file}, empty segments skipped."""
    bucket, key = s3_util.get_bucket_and_key("s3://my-bucket/input", tenant_id, "doc.pdf")
    assert bucket == "my-bucket"
    assert key == expected_key


def test_get_bucket_and_key_no_prefix():
    """A location with no prefix yields a tenant-scoped key with no leading slash."""
    bucket, key = s3_util.get_bucket_and_key("s3://my-bucket", "tenant-a", "doc.pdf")
    assert bucket == "my-bucket"
    assert key == "tenant-a/doc.pdf"
