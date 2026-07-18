#!/usr/bin/env python3
"""Verify the Postman collection covers exactly the OpenAPI spec's endpoints.

The collection is generated from openapi.json, but `openapi-to-postmanv2` emits
random ids, timestamps, and example values each run, so it can't be byte-diffed.
Instead we compare the *set of endpoints* (method + path) in the collection
against the spec - which is what actually drifts when a route is added or removed
and the collection isn't regenerated. Run `make postman` to fix any mismatch.

Usage: python3 check_collection.py [openapi.json] [collection.json]
"""

import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent
DEFAULT_SPEC = HERE / ".." / "openapi.json"
DEFAULT_COLLECTION = HERE / "DocumentAI.postman_collection.json"

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def _norm(path: str) -> str:
    """Normalize path params so `:job_id` (Postman) and `{job_id}` (OpenAPI) match."""
    parts = []
    for seg in path.split("/"):
        if seg.startswith(":") or (seg.startswith("{") and seg.endswith("}")):
            parts.append("{}")
        else:
            parts.append(seg)
    return "/".join(parts) or "/"


def spec_endpoints(spec: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (method.upper(), _norm(path))
        for path, ops in spec.get("paths", {}).items()
        for method in ops
        if method.lower() in HTTP_METHODS
    }


def collection_endpoints(collection: dict[str, Any]) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()

    def walk(items: list[dict[str, Any]]) -> None:
        for it in items:
            if "item" in it:
                walk(it["item"])
            elif "request" in it:
                req = it["request"]
                path = "/" + "/".join(str(s) for s in req.get("url", {}).get("path", []))
                out.add((req.get("method", "").upper(), _norm(path)))

    walk(collection.get("item", []))
    return out


def main() -> None:
    spec_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SPEC
    coll_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_COLLECTION

    spec = spec_endpoints(json.loads(spec_path.read_text()))
    coll = collection_endpoints(json.loads(coll_path.read_text()))

    missing = spec - coll  # in the API but not the collection
    extra = coll - spec  # in the collection but not the API
    if missing or extra:
        for m, p in sorted(missing):
            print(f"  MISSING from collection: {m} {p}")
        for m, p in sorted(extra):
            print(f"  STALE in collection:     {m} {p}")
        sys.exit("Postman collection is out of sync with openapi.json - run `make postman`.")

    print(f"Postman collection matches openapi.json ({len(spec)} endpoints).")


if __name__ == "__main__":
    main()
