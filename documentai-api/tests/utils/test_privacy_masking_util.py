"""Tests for utils/privacy_masking.py."""

from documentai_api.config.privacy_masks import (
    DEMO_EMAIL_DOMAINS,
    DEMO_FIRST_NAMES,
    DEMO_LAST_NAMES,
    DEMO_TENANTS,
)
from documentai_api.utils.privacy_masking import (
    MaskedTenant,
    MaskedUser,
    _hash,
    mask_email,
    mask_tenant,
    mask_user,
)

##############################################################################
# _hash
##############################################################################


def test_hash_is_deterministic():
    assert _hash("foo") == _hash("foo")


def test_hash_different_inputs_differ():
    assert _hash("foo") != _hash("bar")


def test_hash_non_negative():
    assert _hash("anything") >= 0


def test_hash_empty_string_is_deterministic():
    # sha256 of "" is a large non-zero integer; just assert stable output.
    assert _hash("") == _hash("")


##############################################################################
# mask_tenant
##############################################################################


def test_mask_tenant_returns_masked_tenant():
    assert isinstance(mask_tenant("acme"), MaskedTenant)


def test_mask_tenant_name_in_list():
    assert mask_tenant("acme").name in {t["name"] for t in DEMO_TENANTS}


def test_mask_tenant_id_in_list():
    assert mask_tenant("acme").id in {t["id"] for t in DEMO_TENANTS}


def test_mask_tenant_is_deterministic():
    assert mask_tenant("acme") == mask_tenant("acme")


def test_mask_tenant_id_and_name_are_paired():
    result = mask_tenant("some-agency")
    entry = next(t for t in DEMO_TENANTS if t["name"] == result.name)
    assert result.id == entry["id"]


def test_mask_tenant_same_display_name_different_tenant_id_differs():
    r1 = mask_tenant("e2e-test-tenant-gw0")
    r2 = mask_tenant("e2e-test-tenant-gw1")
    assert r1 != r2


def test_mask_tenant_different_inputs_can_differ():
    results = {mask_tenant(f"tenant-id-{i}").name for i in range(20)}
    assert len(results) > 1


##############################################################################
# mask_user
##############################################################################


def test_mask_user_returns_masked_user():
    result = mask_user("user@example.com")
    assert isinstance(result, MaskedUser)


def test_mask_user_first_name_in_list():
    assert mask_user("user@example.com").first in DEMO_FIRST_NAMES


def test_mask_user_last_name_in_list():
    assert mask_user("user@example.com").last in DEMO_LAST_NAMES


def test_mask_user_email_domain_in_list():
    email = mask_user("user@example.com").email
    domain = email.split("@")[1]
    assert domain in DEMO_EMAIL_DOMAINS


def test_mask_user_email_format():
    result = mask_user("user@example.com")
    local, _ = result.email.split("@")
    first_initial, last = local.split(".")
    assert first_initial == result.first[0].lower()
    assert last == result.last.lower()


def test_mask_user_is_deterministic():
    assert mask_user("user@example.com") == mask_user("user@example.com")


def test_mask_user_different_inputs_produce_different_identities():
    results = {mask_user(f"user{i}@example.com").email for i in range(20)}
    assert len(results) > 1


##############################################################################
# mask_email (convenience wrapper)
##############################################################################


def test_mask_email_matches_mask_user_email():
    value = "someone@example.com"
    assert mask_email(value) == mask_user(value).email


def test_mask_email_is_deterministic():
    assert mask_email("a@b.com") == mask_email("a@b.com")
