"""Shared helpers for e2e tests that make real HTTP calls."""

from typing import Any

import requests


def api_headers(api_key: str) -> dict[str, str]:
    return {"API-Key": api_key}


def api_request(
    method: str,
    base_url: str,
    path: str,
    api_key: str | None = None,
    expected_status: int = 200,
    headers: dict[str, str] | None = None,
    **kwargs: Any,
) -> requests.Response:
    """Make an authenticated request and assert the status code."""
    resolved_headers = headers if headers is not None else api_headers(api_key or "")
    r = requests.request(
        method,
        f"{base_url}{path}",
        headers=resolved_headers,
        timeout=30,
        **kwargs,
    )
    assert r.status_code == expected_status, f"{method} {path} -> {r.status_code}: {r.text}"
    return r
