"""Tests for utils/json_parsing.py."""

from documentai_api.utils.json_parsing import parse_json_object


def test_parse_json_object_valid():
    assert parse_json_object('{"key": "value"}', context="test") == {"key": "value"}


def test_parse_json_object_valid_bytes():
    assert parse_json_object(b'{"num": 1}', context="test") == {"num": 1}


def test_parse_json_object_list_returns_none():
    assert parse_json_object("[1, 2, 3]", context="test") is None


def test_parse_json_object_scalar_returns_none():
    assert parse_json_object("42", context="test") is None


def test_parse_json_object_malformed_returns_none():
    assert parse_json_object("{not json", context="test") is None


def test_parse_json_object_invalid_utf8_returns_none():
    assert parse_json_object(b"\xff\xfe", context="test") is None
