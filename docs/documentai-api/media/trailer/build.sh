#!/usr/bin/env bash
# Record the clips, render the narration, and assemble the ~60s trailer video.
#
#   docs/documentai-api/media/trailer/build.sh              # full build with Kokoro voiceover
#   docs/documentai-api/media/trailer/build.sh --no-audio   # silent build (skips the Kokoro step)
#
# Needs: node + `make playwright-install` (Chromium), ffmpeg, uv (for Kokoro).
set -euo pipefail
cd "$(dirname "$0")/../../../.."  # repo root

NO_AUDIO=""
[ "${1:-}" = "--no-audio" ] && NO_AUDIO="--no-audio"

echo "--- Recording demo UI clip ---"
(cd ui/demo && npx playwright test --config=playwright.trailer.config.js)

echo "--- Recording admin console clips ---"
(cd ui/admin && npx playwright test --config=playwright.trailer.config.js)

if [ -z "$NO_AUDIO" ]; then
  echo "--- Rendering narration (Kokoro-ONNX) ---"
  uv run docs/documentai-api/media/trailer/tts_kokoro.py
  echo "--- Building the 60s timeline ---"
  python3 docs/documentai-api/media/trailer/timeline.py
fi

echo "--- Assembling ---"
python3 docs/documentai-api/media/trailer/assemble.py $NO_AUDIO
