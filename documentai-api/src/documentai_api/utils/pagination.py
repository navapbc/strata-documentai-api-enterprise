"""Cursor-based pagination utilities."""

import base64
import json
from typing import Any

from fastapi import HTTPException, status


def encode_cursor(last_key: dict[str, Any]) -> str:
    return base64.urlsafe_b64encode(json.dumps(last_key).encode()).decode()


def decode_cursor(cursor: str) -> dict[str, Any]:
    try:
        result: dict[str, Any] = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return result
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor"
        ) from None
