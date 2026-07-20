"""JSON parsing utilities with safety guards."""

import json
import re
from typing import Any, cast

from documentai_api.logging import get_logger

logger = get_logger(__name__)


def parse_json_object(raw: bytes | str, *, context: str) -> dict[str, Any] | None:
    """json.loads that enforces the result is a JSON object (dict), not a list or scalar."""
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Malformed JSON in {context}: {e}")
        return None
    if not isinstance(parsed, dict):
        logger.error(f"Expected a JSON object in {context}, got {type(parsed).__name__}")
        return None
    return cast(dict[str, Any], parsed)


def parse_llm_json(text: str, *, context: str = "LLM output") -> dict[str, Any] | None:
    """Extract and parse a JSON object from LLM text output.

    Tolerant of common LLM formatting issues:
    - Markdown code fences (```json ... ```)
    - Leading/trailing non-JSON text
    - Unescaped quotes inside string values (e.g. 4-6")

    Returns the parsed dict, or None if no valid JSON object can be extracted.
    """
    # strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"```\s*$", "", cleaned)

    # extract the first JSON object
    json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not json_match:
        logger.warning(f"No JSON object found in {context}: {text[:100]}")
        return None

    raw_json = json_match.group()

    try:
        parsed = json.loads(raw_json)
        if isinstance(parsed, dict):
            return cast(dict[str, Any], parsed)
        return None
    except json.JSONDecodeError:
        pass

    # attempt repair: escape unescaped quotes inside string values
    try:
        repaired = re.sub(r'(?<=\w)"(?=[^:,}\]\s])', r'\\"', raw_json)
        parsed = json.loads(repaired)
        if isinstance(parsed, dict):
            return cast(dict[str, Any], parsed)
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON from {context} after repair: {e}")
        return None
