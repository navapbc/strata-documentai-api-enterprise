"""Tests for utils/s3.py."""

import pytest

from documentai_api.config.env import get_env_config
from documentai_api.generated.env_var_names_generated import EnvVarNames
from documentai_api.utils import s3 as s3_util


@pytest.fixture(autouse=True)
def clear_env_config_cache():
    get_env_config.cache_clear()
    yield
    get_env_config.cache_clear()


@pytest.mark.parametrize(
    ("s3_uri", "expected_bucket", "expected_key"),
    [
        ("s3://bucket/key", "bucket", "key"),
        ("s3://my-bucket/path/to/file.json", "my-bucket", "path/to/file.json"),
        ("s3://bucket/prefix/input/file.pdf", "bucket", "prefix/input/file.pdf"),
        ("s3://bucket", "bucket", ""),  # No key
        (
            "s3://my-bucket/input/tenant123/paystub_2026-09-11#-abc123.pdf",
            "my-bucket",
            "input/tenant123/paystub_2026-09-11#-abc123.pdf",
        ),  # hash in key
    ],
)
def test_parse_s3_uri(s3_uri, expected_bucket, expected_key):
    """Parse S3 URIs into bucket and key."""
    bucket, key = s3_util.parse_s3_uri(s3_uri)
    assert bucket == expected_bucket
    assert key == expected_key


def test_parse_s3_uri_raises_on_invalid_scheme():
    """Non-s3:// URIs raise ValueError."""
    with pytest.raises(ValueError, match="Invalid S3 URI"):
        s3_util.parse_s3_uri("https://bucket/key")


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
    key, bucket = s3_util.extract_s3_info_from_event(event)  # type: ignore[misc]
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
    key, bucket = s3_util.extract_s3_info_from_event(event)  # type: ignore[misc]
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
    key, _ = s3_util.extract_s3_info_from_event(event)  # type: ignore[misc]
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
        ("test-tenant-id", "input/test-tenant-id/doc.pdf"),
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
    bucket, key = s3_util.get_bucket_and_key("s3://my-bucket", "test-tenant-id", "doc.pdf")
    assert bucket == "my-bucket"
    assert key == "test-tenant-id/doc.pdf"


def test_write_extraction_output_uri(monkeypatch, mocker):
    """write_extraction_output returns a correctly tenant-scoped URI."""
    monkeypatch.setenv(EnvVarNames.DOCUMENTAI_OUTPUT_LOCATION, "s3://output-bucket/processed")
    mock_put = mocker.patch("documentai_api.utils.s3.s3_service.put_object")

    uri = s3_util.write_extraction_output(
        "tenant-a", "textract", "doc-uuid", b"data", "application/json"
    )

    assert uri == "s3://output-bucket/processed/tenant-a/doc-uuid/textract/result.json"
    mock_put.assert_called_once()


def test_write_extraction_output_raises_without_tenant(monkeypatch, mocker):
    """write_extraction_output raises if tenant_id is empty."""
    monkeypatch.setenv(EnvVarNames.DOCUMENTAI_OUTPUT_LOCATION, "s3://output-bucket/processed")
    mocker.patch("documentai_api.utils.s3.s3_service.put_object")

    with pytest.raises(ValueError, match="tenant_id is required"):
        s3_util.write_extraction_output("", "textract", "doc-uuid.json", b"data")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Aug\xe2\x80\x94Sep.pdf", "Aug___Sep.pdf"),
        ("Any Questions?.pdf", "Any Questions?.pdf"),
        ("hello-world_2026.pdf", "hello-world_2026.pdf"),
        ("invoice-hyphen-final.PDF—copy", "invoice-hyphen-final.PDF_copy"),
        ("invoice—emdash-final.PDF—copy", "invoice_emdash-final.PDF_copy"),
        ("Invoice March 2026.pdf", "Invoice March 2026.pdf"),  # space preserved
        ("paystub_2026-09-11#-abc123.pdf", "paystub_2026-09-11_-abc123.pdf"),
        ('weird{}^%][\\"><~`|name.pdf', "weird_____________name.pdf"),
        ("\x7fdel.pdf", "_del.pdf"),  # DEL
        ("\ttab.pdf", "_tab.pdf"),  # control char
    ],
)
def test_sanitize_for_s3_key(value, expected):
    assert s3_util.sanitize_for_s3_key(value) == expected


# === get_lifecycle_expiration_days ===


def test_lifecycle_returns_none_when_no_rules_match(mocker):
    mocker.patch(
        "documentai_api.utils.s3.s3_service.get_bucket_lifecycle_configuration",
        return_value={"Rules": []},
    )
    assert s3_util.get_lifecycle_expiration_days("test-bucket", "input/tenant/file.pdf") is None


def test_lifecycle_matches_prefix(mocker):
    mocker.patch(
        "documentai_api.utils.s3.s3_service.get_bucket_lifecycle_configuration",
        return_value={
            "Rules": [
                {"Status": "Enabled", "Filter": {"Prefix": "input/"}, "Expiration": {"Days": 30}},
            ]
        },
    )
    assert s3_util.get_lifecycle_expiration_days("test-bucket", "input/tenant/file.pdf") == 30


def test_lifecycle_longest_prefix_wins(mocker):
    mocker.patch(
        "documentai_api.utils.s3.s3_service.get_bucket_lifecycle_configuration",
        return_value={
            "Rules": [
                {"Status": "Enabled", "Filter": {"Prefix": ""}, "Expiration": {"Days": 90}},
                {"Status": "Enabled", "Filter": {"Prefix": "input/"}, "Expiration": {"Days": 30}},
            ]
        },
    )
    assert s3_util.get_lifecycle_expiration_days("test-bucket", "input/tenant/file.pdf") == 30


def test_lifecycle_skips_and_filter(mocker):
    mocker.patch(
        "documentai_api.utils.s3.s3_service.get_bucket_lifecycle_configuration",
        return_value={
            "Rules": [
                {
                    "Status": "Enabled",
                    "Filter": {"And": {"Prefix": "input/", "Tags": [{"Key": "k", "Value": "v"}]}},
                    "Expiration": {"Days": 30},
                },
            ]
        },
    )
    assert s3_util.get_lifecycle_expiration_days("test-bucket", "input/tenant/file.pdf") is None


def test_lifecycle_skips_disabled_rules(mocker):
    mocker.patch(
        "documentai_api.utils.s3.s3_service.get_bucket_lifecycle_configuration",
        return_value={
            "Rules": [
                {"Status": "Disabled", "Filter": {"Prefix": "input/"}, "Expiration": {"Days": 30}},
            ]
        },
    )
    assert s3_util.get_lifecycle_expiration_days("test-bucket", "input/tenant/file.pdf") is None


def test_lifecycle_caches_on_failure(mocker):
    mock_fetch = mocker.patch(
        "documentai_api.utils.s3.s3_service.get_bucket_lifecycle_configuration",
        side_effect=Exception("AccessDenied"),
    )
    s3_util.get_lifecycle_expiration_days("test-bucket", "input/file.pdf")
    s3_util.get_lifecycle_expiration_days("test-bucket", "input/file.pdf")
    mock_fetch.assert_called_once()


def test_lifecycle_caches_rules(mocker):
    mock_fetch = mocker.patch(
        "documentai_api.utils.s3.s3_service.get_bucket_lifecycle_configuration",
        return_value={
            "Rules": [
                {"Status": "Enabled", "Filter": {"Prefix": "input/"}, "Expiration": {"Days": 30}},
            ]
        },
    )
    s3_util.get_lifecycle_expiration_days("test-bucket", "input/a.pdf")
    s3_util.get_lifecycle_expiration_days("test-bucket", "input/b.pdf")
    mock_fetch.assert_called_once()


# === assert_object_exists ===


def test_assert_object_exists_passes_when_object_present(mocker):
    mocker.patch("documentai_api.utils.s3.s3_service.head_object")
    s3_util.assert_object_exists("test-bucket", "input/file.pdf")  # should not raise


def test_assert_object_exists_raises_404_on_nosuchkey(mocker):
    from botocore.exceptions import ClientError
    from fastapi import HTTPException

    mocker.patch(
        "documentai_api.utils.s3.s3_service.head_object",
        side_effect=ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not Found"}}, "HeadObject"
        ),
    )
    mocker.patch(
        "documentai_api.utils.s3.s3_service.get_bucket_lifecycle_configuration",
        return_value={"Rules": []},
    )
    with pytest.raises(HTTPException) as exc_info:
        s3_util.assert_object_exists("test-bucket", "input/file.pdf")
    assert exc_info.value.status_code == 404


def test_assert_object_exists_raises_404_on_404_code(mocker):
    from botocore.exceptions import ClientError
    from fastapi import HTTPException

    mocker.patch(
        "documentai_api.utils.s3.s3_service.head_object",
        side_effect=ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject"),
    )
    mocker.patch(
        "documentai_api.utils.s3.s3_service.get_bucket_lifecycle_configuration",
        return_value={"Rules": []},
    )
    with pytest.raises(HTTPException) as exc_info:
        s3_util.assert_object_exists("test-bucket", "input/file.pdf")
    assert exc_info.value.status_code == 404


def test_assert_object_exists_includes_lifecycle_days_in_message(mocker):
    from botocore.exceptions import ClientError
    from fastapi import HTTPException

    mocker.patch(
        "documentai_api.utils.s3.s3_service.head_object",
        side_effect=ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not Found"}}, "HeadObject"
        ),
    )
    mocker.patch(
        "documentai_api.utils.s3.s3_service.get_bucket_lifecycle_configuration",
        return_value={
            "Rules": [
                {"Status": "Enabled", "Filter": {"Prefix": "input/"}, "Expiration": {"Days": 30}},
            ]
        },
    )
    with pytest.raises(HTTPException) as exc_info:
        s3_util.assert_object_exists("test-bucket", "input/file.pdf")
    assert "30 days" in exc_info.value.detail


def test_assert_object_exists_reraises_non_404_client_error(mocker):
    from botocore.exceptions import ClientError

    mocker.patch(
        "documentai_api.utils.s3.s3_service.head_object",
        side_effect=ClientError({"Error": {"Code": "403", "Message": "Forbidden"}}, "HeadObject"),
    )
    with pytest.raises(ClientError):
        s3_util.assert_object_exists("test-bucket", "input/file.pdf")
