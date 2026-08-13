#!/usr/bin/env python3
"""Apply local-dev defaults to a generated Postman collection.

`openapi-to-postmanv2` produces a faithful but generic collection from the
OpenAPI spec; it has no way to know the local dev base URL, the shared API key,
or that this API authenticates with an `API-Key` header. This script layers
those conveniences on so the collection is usable the moment it's imported.

Run as a post-process step of build.sh (or directly):
    python3 patch_collection.py [path/to/collection.json]

Defaults to the DocumentAI collection next to this script.
"""

import json
import sys
from pathlib import Path

DEFAULT_COLLECTION = Path(__file__).parent / "DocumentAI.postman_collection.json"

DESCRIPTION = (
    "DocumentAI API collection, generated from docs/documentai-api/openapi.json.\n\n"
    "Quick start (local dev):\n"
    "1. Start the API: `cd documentai-api && cp local.env.example .env && make init && make start` "
    "(serves http://localhost:8000).\n"
    "2. This collection sends `API-Key: {{apiKey}}` on every request; the default matches the local dev key.\n"
    "3. Admin (`/v1/admin/*`) routes require a Cognito JWT and will 401/403 with only the API key.\n\n"
    "Regenerate with `make postman`."
)

VARIABLES = [
    {"key": "baseUrl", "value": "http://localhost:8000", "type": "string"},
    {"key": "apiKey", "value": "local-dev-key", "type": "string"},
]

# Collection-level API-Key header auth (the API expects the `API-Key` header).
AUTH = {
    "type": "apikey",
    "apikey": [
        {"key": "key", "value": "API-Key", "type": "string"},
        {"key": "value", "value": "{{apiKey}}", "type": "string"},
        {"key": "in", "value": "header", "type": "string"},
    ],
}


def patch(path: Path) -> None:
    collection = json.loads(path.read_text())
    collection["info"]["description"] = DESCRIPTION
    collection["variable"] = VARIABLES
    collection["auth"] = AUTH
    path.write_text(json.dumps(collection, indent=2) + "\n")


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_COLLECTION
    if not path.is_file():
        sys.exit(f"collection not found: {path}")
    patch(path)
    print(f"Patched {path}")


if __name__ == "__main__":
    main()
