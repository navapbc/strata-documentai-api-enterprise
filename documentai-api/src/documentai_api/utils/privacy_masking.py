"""Utilities for masking PII fields in privacy mode responses."""

import hashlib
from dataclasses import dataclass

from documentai_api.config.privacy_masks import (
    DEMO_EMAIL_DOMAINS,
    DEMO_FIRST_NAMES,
    DEMO_LAST_NAMES,
    DEMO_TENANTS,
)


@dataclass
class MaskedUser:
    """Masked identity derived from a single source value."""

    first: str
    last: str
    email: str


def _hash(value: str) -> int:
    """Deterministic sha256-based hash so the same input always maps to the same masked output."""
    return int(hashlib.sha256(value.encode()).hexdigest(), 16)


@dataclass
class MaskedTenant:
    """Masked tenant identity derived from a display name."""

    id: str
    name: str


def mask_tenant(tenant_id: str) -> MaskedTenant:
    """Derive a deterministic fake tenant identity from a tenant ID."""
    tenant = DEMO_TENANTS[_hash(tenant_id) % len(DEMO_TENANTS)]
    return MaskedTenant(id=tenant["id"], name=tenant["name"])


def mask_user(value: str) -> MaskedUser:
    """Derive a deterministic fake identity from an email or username."""
    first = DEMO_FIRST_NAMES[_hash(value) % len(DEMO_FIRST_NAMES)]
    last = DEMO_LAST_NAMES[_hash(value + "last") % len(DEMO_LAST_NAMES)]
    domain = DEMO_EMAIL_DOMAINS[_hash(value + "domain") % len(DEMO_EMAIL_DOMAINS)]
    return MaskedUser(first=first, last=last, email=f"{first[0].lower()}.{last.lower()}@{domain}")


def mask_email(value: str) -> str:
    """Convenience wrapper returning just the masked email for a given value."""
    return mask_user(value).email
