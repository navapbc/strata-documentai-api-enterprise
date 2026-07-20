"""Tests for utils/json_parsing.py."""

from documentai_api.utils.json_parsing import parse_json_object, parse_llm_json


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


def test_parse_llm_json_clean():
    assert parse_llm_json('{"key": "value"}') == {"key": "value"}


def test_parse_llm_json_with_surrounding_text():
    text = 'Here is the result:\n{"fields": [{"name": "test"}]}\nDone.'
    result = parse_llm_json(text)
    assert result == {"fields": [{"name": "test"}]}


def test_parse_llm_json_markdown_fences():
    text = '```json\n{"key": "value"}\n```'
    assert parse_llm_json(text) == {"key": "value"}


def test_parse_llm_json_unescaped_quote():
    """LLMs emit values like 4-6" which break json.loads."""
    text = '{"fields": [{"value": "4-6"", "name": "height"}]}'
    result = parse_llm_json(text)
    assert result is not None
    assert result["fields"][0]["value"] == '4-6"'


def test_parse_llm_json_no_json_returns_none():
    assert parse_llm_json("No JSON here, just text.") is None


def test_parse_llm_json_completely_broken_returns_none():
    assert parse_llm_json("{{{not valid at all}}}") is None
