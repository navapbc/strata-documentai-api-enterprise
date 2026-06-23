"""JSON parsing utilities with safety guards."""

import json
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
