#!/usr/bin/env bash
# Regenerate the Postman collection from the committed OpenAPI spec, then apply
# local-dev defaults (baseUrl/apiKey variables + API-Key header auth).
#
# Run via `make postman` from the repo root, or directly:  postman/build.sh
#
# If the API surface changed, regenerate the spec first:
#   cd documentai-api && uv run python -m documentai_api.cli.export_openapi > ../docs/documentai-api/openapi.json
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
SPEC="$DIR/../openapi.json"
OUT="$DIR/DocumentAI.postman_collection.json"

# Pinned so regeneration is deterministic (a newer converter could change output
# and break the CI drift check). Bump deliberately, then re-run `make postman`.
npx -y openapi-to-postmanv2@6.3.0 -s "$SPEC" -o "$OUT" -p -O folderStrategy=Tags

# Layer on local-dev defaults (baseUrl/apiKey variables + API-Key auth) that the
# generic OpenAPI conversion can't infer.
python3 "$DIR/patch_collection.py" "$OUT"

echo "Wrote $OUT"
