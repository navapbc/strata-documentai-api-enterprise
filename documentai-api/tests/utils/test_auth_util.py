"""Tests for utils/auth.py."""

import hashlib
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from documentai_api.config.env import EnvVars
from documentai_api.schemas.api_key import ApiKeyRecord
from documentai_api.utils import auth as auth_util
from documentai_api.utils.cache import get_cache


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the in-memory auth key cache between tests.

    Draining leaked lastUsed updater threads and resetting ``_last_used_written_at``
    is handled suite-wide by the autouse ``drain_lastused_threads`` fixture in
    tests/conftest.py.
    """
    get_cache().clear()
    yield
    get_cache().clear()


@pytest.fixture
def seed_api_key(api_keys_table):
    """Factory fixture to create an API key and return (raw_key, key_hash)."""

    def _seed(
        api_key_name="test-client", environment="prod", expires_at=None, tenant_id="test-tenant"
    ):
        api_key, _ = auth_util.generate_api_key(
            api_key_name, environment, tenant_id=tenant_id, expires_at=expires_at
        )
        return api_key, auth_util._hash_key(api_key)

    return _seed


##############################################################################
# _hash_key
##############################################################################


def test_hash_key_returns_sha256():
    result = auth_util._hash_key("my-api-key")
    expected = hashlib.sha256(b"my-api-key").hexdigest()
    assert result == expected


def test_hash_key_different_inputs_produce_different_hashes():
    assert auth_util._hash_key("key-1") != auth_util._hash_key("key-2")


##############################################################################
# _get_cache_ttl
##############################################################################


def test_get_cache_ttl_default(monkeypatch):
    monkeypatch.delenv(EnvVars.API_AUTH_CACHE_TTL, raising=False)
    assert auth_util._get_cache_ttl_minutes() == 5


def test_get_cache_ttl_from_env(monkeypatch):
    monkeypatch.setenv(EnvVars.API_AUTH_CACHE_TTL, "120")
    assert auth_util._get_cache_ttl_minutes() == 2


def test_get_cache_ttl_invalid_value(monkeypatch):
    monkeypatch.setenv(EnvVars.API_AUTH_CACHE_TTL, "not-a-number")
    assert auth_util._get_cache_ttl_minutes() == 5


##############################################################################
# _get_from_cache / _set_cache
##############################################################################


def test_cache_miss_returns_none():
    assert get_cache().get("nonexistent-hash") is None


def test_cache_hit_returns_record():
    record = {ApiKeyRecord.KEY_HASH: "abc", ApiKeyRecord.IS_ACTIVE: True}
    get_cache().add("abc", record, ttl_minutes=5)
    assert get_cache().get("abc") == record


def test_cache_expired_returns_none():
    from datetime import datetime, timedelta

    from documentai_api.utils.cache import CacheItem

    record = {ApiKeyRecord.KEY_HASH: "abc", ApiKeyRecord.IS_ACTIVE: True}
    get_cache().add("abc", record, ttl_minutes=5)

    # manually expire the cache entry
    expired_item = CacheItem(record, ttl_minutes=1)
    expired_item.expires_at = datetime.now() - timedelta(minutes=1)
    get_cache()._cache["abc"] = expired_item

    assert get_cache().get("abc") is None


##############################################################################
# _validate_key_record
##############################################################################


def test_validate_key_record_active():
    assert auth_util._validate_key_record({ApiKeyRecord.IS_ACTIVE: True}) is True


def test_validate_key_record_inactive():
    assert auth_util._validate_key_record({ApiKeyRecord.IS_ACTIVE: False}) is False


def test_validate_key_record_missing_is_active():
    assert auth_util._validate_key_record({}) is False


def test_validate_key_record_not_expired():
    from datetime import UTC, datetime, timedelta

    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    assert (
        auth_util._validate_key_record(
            {ApiKeyRecord.IS_ACTIVE: True, ApiKeyRecord.EXPIRES_AT: future}
        )
        is True
    )


def test_validate_key_record_expired():
    from datetime import UTC, datetime, timedelta

    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    assert (
        auth_util._validate_key_record(
            {ApiKeyRecord.IS_ACTIVE: True, ApiKeyRecord.EXPIRES_AT: past}
        )
        is False
    )


def test_validate_key_record_invalid_expires_at():
    assert (
        auth_util._validate_key_record(
            {ApiKeyRecord.IS_ACTIVE: True, ApiKeyRecord.EXPIRES_AT: "not-a-date"}
        )
        is False
    )


##############################################################################
# _verify_with_insecure_shared_key
##############################################################################


def test_insecure_key_missing_env_raises_500(monkeypatch):
    monkeypatch.delenv(EnvVars.API_AUTH_INSECURE_SHARED_KEY, raising=False)
    with pytest.raises(HTTPException) as exc_info:
        auth_util._verify_with_insecure_shared_key("any-key")
    assert exc_info.value.status_code == 500


def test_insecure_key_invalid_raises_401(monkeypatch):
    monkeypatch.setenv(EnvVars.API_AUTH_INSECURE_SHARED_KEY, "correct-key")
    with pytest.raises(HTTPException) as exc_info:
        auth_util._verify_with_insecure_shared_key("wrong-key")
    assert exc_info.value.status_code == 401


def test_insecure_key_missing_header_raises_401(monkeypatch):
    monkeypatch.setenv(EnvVars.API_AUTH_INSECURE_SHARED_KEY, "correct-key")
    with pytest.raises(HTTPException) as exc_info:
        auth_util._verify_with_insecure_shared_key(None)
    assert exc_info.value.status_code == 401


def test_insecure_key_valid_passes(monkeypatch):
    monkeypatch.setenv(EnvVars.API_AUTH_INSECURE_SHARED_KEY, "correct-key")
    auth_util._verify_with_insecure_shared_key("correct-key")  # should not raise


##############################################################################
# _is_valid_key_format
##############################################################################


def test_valid_key_format():
    assert auth_util._is_valid_key_format("docai_" + "a" * 32) is True


def test_invalid_key_format_wrong_prefix():
    assert auth_util._is_valid_key_format("dde_prod_" + "a" * 32) is False


def test_invalid_key_format_too_short():
    assert auth_util._is_valid_key_format("docai_short") is False


def test_invalid_key_format_empty():
    assert auth_util._is_valid_key_format("") is False


def test_invalid_key_format_none():
    assert auth_util._is_valid_key_format(None) is False


##############################################################################
# _verify_with_ddb (moto-backed)
##############################################################################


def test_ddb_verify_missing_key_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        auth_util._verify_with_ddb(None)
    assert exc_info.value.status_code == 401


def test_ddb_verify_rejects_invalid_format():
    with pytest.raises(HTTPException) as exc_info:
        auth_util._verify_with_ddb("not-a-valid-key")
    assert exc_info.value.status_code == 401


def test_ddb_verify_key_not_in_ddb_raises_401(api_keys_table):
    with pytest.raises(HTTPException) as exc_info:
        auth_util._verify_with_ddb("docai_" + "a" * 32)
    assert exc_info.value.status_code == 401


def test_ddb_verify_inactive_key_raises_401(api_keys_table):
    raw_key = "docai_" + "b" * 32
    key_hash = auth_util._hash_key(raw_key)
    api_keys_table.put_item(
        Item={
            ApiKeyRecord.KEY_HASH: key_hash,
            ApiKeyRecord.API_KEY_NAME: "test-client",
            ApiKeyRecord.IS_ACTIVE: False,
        }
    )
    with pytest.raises(HTTPException) as exc_info:
        auth_util._verify_with_ddb(raw_key)
    assert exc_info.value.status_code == 401


def test_ddb_verify_valid_key_passes(api_keys_table):
    raw_key = "docai_" + "c" * 32
    key_hash = auth_util._hash_key(raw_key)
    api_keys_table.put_item(
        Item={
            ApiKeyRecord.KEY_HASH: key_hash,
            ApiKeyRecord.API_KEY_NAME: "test-client",
            ApiKeyRecord.IS_ACTIVE: True,
        }
    )
    auth_util._verify_with_ddb(raw_key)  # should not raise


def test_ddb_verify_uses_cache_on_second_call(api_keys_table):
    raw_key = "docai_" + "d" * 32
    key_hash = auth_util._hash_key(raw_key)
    api_keys_table.put_item(
        Item={
            ApiKeyRecord.KEY_HASH: key_hash,
            ApiKeyRecord.API_KEY_NAME: "test-client",
            ApiKeyRecord.IS_ACTIVE: True,
        }
    )
    with patch(
        "documentai_api.utils.auth._lookup_key_in_ddb", wraps=auth_util._lookup_key_in_ddb
    ) as spy:
        auth_util._verify_with_ddb(raw_key)
        auth_util._verify_with_ddb(raw_key)
        spy.assert_called_once()  # second call hits cache


##############################################################################
# _update_last_used (behavior tests - patches needed for debounce/threading)
##############################################################################


@pytest.fixture
def pinned_api_keys_config():
    """Pin get_aws_config for _update_last_used tests."""
    with patch("documentai_api.utils.auth.get_aws_config") as mock_config:
        mock_config.return_value.api_keys_table_name = "api-keys"
        yield


def test_update_last_used_debounced_skips_second_call(pinned_api_keys_config):
    with patch("documentai_api.services.ddb.update_item") as mock_update:
        auth_util._update_last_used("test-hash")
        auth_util._update_last_used("test-hash")  # should be skipped
        mock_update.assert_called_once()


def test_update_last_used_writes_after_debounce_period(pinned_api_keys_config):
    with patch("documentai_api.services.ddb.update_item") as mock_update:
        auth_util._update_last_used("test-hash")
        # expire the debounce window
        auth_util._last_used_written_at["test-hash"] = 0
        auth_util._update_last_used("test-hash")  # should write again
        assert mock_update.call_count == 2


def test_update_last_used_writes_to_ddb(pinned_api_keys_config):
    with patch("documentai_api.services.ddb.update_item") as mock_update:
        auth_util._update_last_used("test-hash")
        mock_update.assert_called_once()
        kwargs = mock_update.call_args.kwargs
        assert ":lastUsed" in kwargs["expression_values"]
        assert kwargs["key"] == {ApiKeyRecord.KEY_HASH: "test-hash"}


def test_update_last_used_silently_ignores_errors(pinned_api_keys_config):
    with patch("documentai_api.services.ddb.update_item", side_effect=Exception("DDB error")):
        auth_util._update_last_used("test-hash")  # should not raise


def test_update_last_used_dict_is_bounded(pinned_api_keys_config, monkeypatch):
    """The lastUsed debounce map must not grow without bound (one entry per key)."""
    monkeypatch.setattr(auth_util, "_LAST_USED_MAX_ENTRIES", 100)
    with patch("documentai_api.services.ddb.update_item"):
        for i in range(1000):
            auth_util._update_last_used(f"hash-{i}")
    assert len(auth_util._last_used_written_at) == 100
    # The most recently written hashes are retained; the oldest are evicted.
    assert "hash-999" in auth_util._last_used_written_at
    assert "hash-0" not in auth_util._last_used_written_at


##############################################################################
# generate_api_key (moto-backed)
##############################################################################


def test_generate_api_key_writes_to_ddb(seed_api_key, api_keys_table):
    """Test generate_api_key stores the hash in DDB."""
    api_key, key_hash = seed_api_key(api_key_name="my-service", environment="prod")

    assert api_key.startswith("docai_")

    item = api_keys_table.get_item(Key={ApiKeyRecord.KEY_HASH: key_hash})["Item"]

    assert item is not None
    assert item[ApiKeyRecord.API_KEY_NAME] == "my-service"
    assert item[ApiKeyRecord.ENVIRONMENT] == "prod"
    assert item[ApiKeyRecord.IS_ACTIVE] is True
    assert ApiKeyRecord.CREATED_AT in item
    assert api_key not in str(item)  # plaintext not stored


def test_generate_api_key_warns_existing_via_ddb(seed_api_key, api_keys_table):
    """Test generate_api_key detects existing active keys via real DDB scan."""
    seed_api_key(api_key_name="my-service")

    _, existing = auth_util.generate_api_key("my-service", "prod", "test-tenant")

    assert len(existing) == 1
    assert existing[0][ApiKeyRecord.API_KEY_NAME] == "my-service"


def test_generate_api_key_existing_warning_is_tenant_scoped(seed_api_key, api_keys_table):
    """A same-named active key in another tenant must not be reported as existing."""
    seed_api_key(api_key_name="my-service", tenant_id="tenant-a")

    _, existing = auth_util.generate_api_key("my-service", "prod", "tenant-b")

    assert existing == []


def test_generate_api_key_with_expires_at(seed_api_key, api_keys_table):
    from datetime import UTC, datetime, timedelta

    expires = datetime.now(UTC) + timedelta(days=90)
    _, key_hash = seed_api_key(api_key_name="my-service", expires_at=expires)

    item = api_keys_table.get_item(Key={ApiKeyRecord.KEY_HASH: key_hash})["Item"]
    assert ApiKeyRecord.EXPIRES_AT in item


##############################################################################
# deactivate_api_key (moto-backed)
##############################################################################


def test_deactivate_api_key_found(seed_api_key, api_keys_table):
    _, key_hash = seed_api_key()

    result = auth_util.deactivate_api_key(key_hash)

    assert result is True
    item = api_keys_table.get_item(Key={ApiKeyRecord.KEY_HASH: key_hash})["Item"]
    assert item[ApiKeyRecord.IS_ACTIVE] is False


def test_deactivate_api_key_not_found(api_keys_table):
    result = auth_util.deactivate_api_key("nonexistent-hash")
    assert result is False


def test_deactivate_api_key_invalidates_cache(seed_api_key):
    _, key_hash = seed_api_key()

    # Prime the cache by verifying the key
    get_cache().add(key_hash, {ApiKeyRecord.IS_ACTIVE: True}, ttl_minutes=5)
    assert get_cache().get(key_hash) is not None

    auth_util.deactivate_api_key(key_hash)

    assert get_cache().get(key_hash) is None


##############################################################################
# get_active_keys_by_name (moto-backed)
##############################################################################


def test_get_active_keys_by_name_returns_matching(api_keys_table):
    api_keys_table.put_item(
        Item={
            ApiKeyRecord.KEY_HASH: "hash-1",
            ApiKeyRecord.API_KEY_NAME: "my-service",
            ApiKeyRecord.IS_ACTIVE: True,
        }
    )
    api_keys_table.put_item(
        Item={
            ApiKeyRecord.KEY_HASH: "hash-2",
            ApiKeyRecord.API_KEY_NAME: "my-service",
            ApiKeyRecord.IS_ACTIVE: False,
        }
    )
    api_keys_table.put_item(
        Item={
            ApiKeyRecord.KEY_HASH: "hash-3",
            ApiKeyRecord.API_KEY_NAME: "other-service",
            ApiKeyRecord.IS_ACTIVE: True,
        }
    )

    result = auth_util.get_active_keys_by_name("my-service")

    assert len(result) == 1
    assert result[0][ApiKeyRecord.KEY_HASH] == "hash-1"


def test_get_active_keys_by_name_returns_empty_on_error(monkeypatch):
    monkeypatch.setenv(EnvVars.API_KEYS_TABLE_NAME, "nonexistent-table")
    result = auth_util.get_active_keys_by_name("my-service")
    assert result == []


##############################################################################
# verify_api_key (routing behavior - patches needed)
##############################################################################


def test_verify_api_key_uses_ddb_when_enabled(monkeypatch):
    monkeypatch.setenv(EnvVars.API_AUTH_ENABLED, "true")
    with patch("documentai_api.utils.auth._verify_with_ddb") as mock_ddb:
        auth_util.verify_api_key("docai_" + "a" * 32)
        mock_ddb.assert_called_once_with("docai_" + "a" * 32)


def test_verify_api_key_uses_insecure_key_when_disabled(monkeypatch):
    monkeypatch.setenv(EnvVars.API_AUTH_ENABLED, "false")
    with patch("documentai_api.utils.auth._verify_with_insecure_shared_key") as mock_insecure:
        auth_util.verify_api_key("docai_" + "a" * 32)
        mock_insecure.assert_called_once_with("docai_" + "a" * 32)


def test_verify_api_key_disabled_by_default(monkeypatch):
    monkeypatch.delenv(EnvVars.API_AUTH_ENABLED, raising=False)
    with patch("documentai_api.utils.auth._verify_with_insecure_shared_key") as mock_insecure:
        auth_util.verify_api_key("docai_" + "a" * 32)
        mock_insecure.assert_called_once_with("docai_" + "a" * 32)


##############################################################################
# verify_api_key end-to-end (moto-backed)
##############################################################################


def test_verify_api_key_end_to_end_with_moto(seed_api_key, monkeypatch):
    """Test full verify_api_key → _verify_with_ddb → DDB flow using moto."""
    monkeypatch.setenv(EnvVars.API_AUTH_ENABLED, "true")

    api_key, _ = seed_api_key()

    auth_util.verify_api_key(api_key)  # should not raise


def test_verify_api_key_end_to_end_invalid_key(api_keys_table, monkeypatch):
    """Test full flow rejects a key that doesn't exist in DDB."""
    monkeypatch.setenv(EnvVars.API_AUTH_ENABLED, "true")

    with pytest.raises(HTTPException) as exc_info:
        auth_util.verify_api_key("docai_invalid_key")
    assert exc_info.value.status_code == 401


def test_verify_api_key_end_to_end_deactivated_key(seed_api_key, monkeypatch):
    """Test full flow rejects a deactivated key."""
    monkeypatch.setenv(EnvVars.API_AUTH_ENABLED, "true")

    api_key, key_hash = seed_api_key()
    auth_util.deactivate_api_key(key_hash)

    with pytest.raises(HTTPException) as exc_info:
        auth_util.verify_api_key(api_key)
    assert exc_info.value.status_code == 401


##############################################################################
# _lookup_key_in_ddb (moto-backed)
##############################################################################


def test_lookup_key_in_ddb_found(api_keys_table):
    """Test _lookup_key_in_ddb returns record when key exists in DDB."""
    key_hash = auth_util._hash_key("test-key")
    api_keys_table.put_item(
        Item={
            ApiKeyRecord.KEY_HASH: key_hash,
            ApiKeyRecord.API_KEY_NAME: "test-client",
            ApiKeyRecord.IS_ACTIVE: True,
        }
    )

    result = auth_util._lookup_key_in_ddb(key_hash)

    assert result is not None
    assert result[ApiKeyRecord.API_KEY_NAME] == "test-client"
    assert result[ApiKeyRecord.IS_ACTIVE] is True


def test_lookup_key_in_ddb_not_found(api_keys_table):
    """Test _lookup_key_in_ddb returns None when key does not exist."""
    result = auth_util._lookup_key_in_ddb("nonexistent-hash")
    assert result is None


##############################################################################
# is_duplicate_key_name (moto-backed)
##############################################################################


def test_is_duplicate_key_name_true_when_active_key_exists(api_keys_table):
    api_keys_table.put_item(
        Item={
            ApiKeyRecord.KEY_HASH: "hash-1",
            ApiKeyRecord.API_KEY_NAME: "my-service",
            ApiKeyRecord.TENANT_ID: "tenant-a",
            ApiKeyRecord.IS_ACTIVE: True,
        }
    )
    assert auth_util.is_duplicate_key_name("tenant-a", "my-service") is True


def test_is_duplicate_key_name_false_when_no_keys(api_keys_table):
    assert auth_util.is_duplicate_key_name("tenant-a", "my-service") is False


def test_is_duplicate_key_name_false_when_different_tenant(api_keys_table):
    api_keys_table.put_item(
        Item={
            ApiKeyRecord.KEY_HASH: "hash-1",
            ApiKeyRecord.API_KEY_NAME: "my-service",
            ApiKeyRecord.TENANT_ID: "tenant-b",
            ApiKeyRecord.IS_ACTIVE: True,
        }
    )
    assert auth_util.is_duplicate_key_name("tenant-a", "my-service") is False


def test_is_duplicate_key_name_true_even_when_inactive(api_keys_table):
    """Key names are immutable audit identifiers - reuse is never allowed."""
    api_keys_table.put_item(
        Item={
            ApiKeyRecord.KEY_HASH: "hash-1",
            ApiKeyRecord.API_KEY_NAME: "my-service",
            ApiKeyRecord.TENANT_ID: "tenant-a",
            ApiKeyRecord.IS_ACTIVE: False,
        }
    )
    assert auth_util.is_duplicate_key_name("tenant-a", "my-service") is True


##############################################################################
# scan pagination
##############################################################################


def test_scan_returns_all_pages(api_keys_table):
    """Test that scan() retrieves all items across multiple DynamoDB pages."""
    from unittest.mock import call

    from documentai_api.services import ddb as ddb_service

    page1 = {"Items": [{"keyHash": "a"}], "LastEvaluatedKey": {"keyHash": "a"}}
    page2 = {"Items": [{"keyHash": "b"}], "LastEvaluatedKey": {"keyHash": "b"}}
    page3 = {"Items": [{"keyHash": "c"}]}

    with (
        patch.object(api_keys_table, "scan", side_effect=[page1, page2, page3]) as mock_scan,
        patch(
            "documentai_api.services.ddb.AWSClientFactory.get_ddb_table",
            return_value=api_keys_table,
        ),
    ):
        result = ddb_service.scan("api-keys")

    assert len(result) == 3
    assert mock_scan.call_count == 3
    assert mock_scan.call_args_list[1] == call(ExclusiveStartKey={"keyHash": "a"})
    assert mock_scan.call_args_list[2] == call(ExclusiveStartKey={"keyHash": "b"})
