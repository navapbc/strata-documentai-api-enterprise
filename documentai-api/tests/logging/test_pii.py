import pytest

import documentai_api.logging.pii as pii


@pytest.mark.parametrize(
    ("input", "expected"),
    [
        ("", ""),
        ("1234", "1234"),
        (1234, 1234),
        (None, None),
        ("hostname ip-10-11-12-134.ec2.internal", "hostname ip-10-11-12-134.ec2.internal"),
        ({}, {}),
        ("123456789", "*********"),
        (123456789, "*********"),
        ("123-45-6789", "*********"),
        ("123456789 test", "********* test"),
        ("test 123456789", "test *********"),
        ("test 123456789 test", "test ********* test"),
        ("test=999000000.", "test=*********."),
        ("test=999000000,", "test=*********,"),
        (999000000.5, 999000000.5),
        ({"a": "x", "b": "999000000"}, "{'a': 'x', 'b': '*********'}"),
    ],
)
def test_mask_pii(input, expected):
    assert pii._mask_pii(input) == expected


@pytest.mark.parametrize("status_word", ["FAILED", "PROCESSING", "COMPLETED", "SUCCESS"])
def test_status_words_not_masked(status_word):
    assert pii._mask_pii(status_word) == status_word


def test_status_word_in_log_line_not_masked():
    assert pii._mask_pii("status=COMPLETED") == "status=COMPLETED"


@pytest.mark.parametrize("passport", ["A12345678", "AB1234567"])
def test_passport_number_masked(passport):
    assert pii._mask_pii(passport) == "*********"


@pytest.mark.parametrize(
    "key",
    ["first_name", "last_name", "ssn", "license_number", "passport_number", "date_of_birth"],
)
def test_deny_list_field_masked(key):
    assert pii._mask_pii_for_key(key, "any value") == "*********"


def test_allow_no_mask_field_returned_as_is():
    assert pii._mask_pii_for_key("hostname", "my-host") == "my-host"
