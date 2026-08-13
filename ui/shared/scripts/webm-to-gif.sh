#!/usr/bin/env bash
# Convert a Playwright .webm recording into a compact, high-quality GIF using
# ffmpeg's two-pass palettegen/paletteuse (same approach as the terminal demo).
#
# Usage: scripts/webm-to-gif.sh <input.webm> [output.gif] [fps] [width]
set -euo pipefail

IN="${1:?usage: webm-to-gif.sh <input.webm> [output.gif] [fps] [width]}"
OUT="${2:-${IN%.webm}.gif}"
FPS="${3:-12}"
WIDTH="${4:-900}"

PALETTE="$(mktemp -t palette).png"
trap 'rm -f "$PALETTE"' EXIT

FILTERS="fps=${FPS},scale=${WIDTH}:-1:flags=lanczos"

ffmpeg -v warning -y -i "$IN" -vf "${FILTERS},palettegen=stats_mode=diff" "$PALETTE"
ffmpeg -v warning -y -i "$IN" -i "$PALETTE" \
  -lavfi "${FILTERS} [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle" \
  "$OUT"

echo "Wrote $OUT ($(du -h "$OUT" | cut -f1))"
