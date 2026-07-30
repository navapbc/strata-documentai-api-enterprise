"""Mask PII from log records.

This module defines a filter that can be attached to a logger to mask PII
from log records. The filter is applied to all log records, and masks PII
that looks like social security numbers.

You can add the filter to a handler:

Example:
    import logging
    import documentai_api.logging.pii as pii

    handler = logging.StreamHandler()
    handler.addFilter(pii.mask_pii)
    logger = logging.getLogger(__name__)
    logger.addHandler(handler)

Or you can add the filter directly to a logger.
If adding the filter directly to a logger, take note that the filter
will not be called for child loggers.
See https://docs.python.org/3/library/logging.html#logging.Logger.propagate

Example:
    import logging
    import documentai_api.logging.pii as pii

    logger = logging.getLogger(__name__)
    logger.addFilter(pii.mask_pii)
"""

import logging
import re
from typing import Any


def mask_pii(record: logging.LogRecord) -> bool:
    # Loop through all entries in the record's __dict__
    # attribute and mask any things that look like PII.
    # We will mask positional args separately below.
    record.__dict__ |= {
        key: _mask_pii_for_key(key, value)
        for key, value in record.__dict__.items()
        if key != "args"  # Handle positional "args" separately
    }

    # record.__dict__["args"] will contain positional arguments to logging calls.
    # For example, a call like logger.info("%s %s", "foo", "bar") will result in a LogRecord
    # with record.__dict__["args"] == ("foo", "bar")
    # We want to mask the PII on each argument separately rather than trying to do a PII regex
    # match on the entire args tuple.
    args = record.__dict__["args"]
    record.__dict__["args"] = tuple(map(_mask_pii, args))
    return True


# Regular expression to match a tax identifier (SSN), 9 digits with optional dashes.
# Matches between word boundaries (\b), except when:
#  - Preceded by word character and dash (e.g. "ip-10-11-12-134")
#  - Followed by a dot and digit, for decimal numbers (e.g. 999000000.5)
# See https://docs.python.org/3/library/re.html#regular-expression-syntax
TIN_RE = re.compile(
    r"""
        \b          # word boundary
        (?<!\w-)    # not preceded by word character and dash
        (\d-?){8}   # digit then optional dash, 8 times
        \d          # last digit
        \b          # word boundary
        (?!\.\d)    # not followed by decimal point and digit (for decimal numbers)
    """,
    re.ASCII | re.VERBOSE,
)

# Passport number: letter + 8 digits (US format) or 2 letters + 7 digits (common international).
PASSPORT_RE = re.compile(r"\b[A-Z]{1,2}\d{7,8}\b")

ALLOW_NO_MASK = {
    "account_key",
    "count",
    "created",
    "hostname",
    "process",
    "thread",
}

# Field names whose values should always be masked regardless of value shape.
# Covers identity-document fields returned by BDA that won't match numeric patterns.
_PII_FIELD_DENY_LIST = {
    # Names
    "first_name",
    "last_name",
    "full_name",
    "name",
    "given_name",
    "surname",
    "middle_name",
    # Identity document numbers
    "ssn",
    "tin",
    "license_number",
    "dl_number",
    "driver_license_number",
    "passport_number",
    "document_number",
    "id_number",
    # Addresses / contact
    "address",
    "street_address",
    "date_of_birth",
    "dob",
}


def _mask_pii_for_key(key: str, value: Any | None) -> Any | None:
    """Mask the given value if the key is on the PII deny list or the value matches a known PII pattern.

    Patterns checked: SSN, passport number.
    Keys in ALLOW_NO_MASK are always returned as-is.
    """
    if key in ALLOW_NO_MASK:
        return value
    if key.lower() in _PII_FIELD_DENY_LIST:
        return "*********"
    return _mask_pii(value)


def _mask_pii(value: Any | None) -> Any | None:
    s = str(value)
    if TIN_RE.search(s):
        s = TIN_RE.sub("*********", s)
    if PASSPORT_RE.search(s):
        s = PASSPORT_RE.sub("*********", s)
    return s if s != str(value) else value
