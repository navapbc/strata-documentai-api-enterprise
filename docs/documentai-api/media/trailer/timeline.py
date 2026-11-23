"""Build the 60-second timeline: when each segment starts and ends, from measured speech.

Runs after tts_kokoro.py (build.sh does both) and writes out/timeline.json;
narration.json stays hand-written only. assemble.py retimes each clip to its
segment's window in this timeline.

Each segment needs its speech plus a lead-in and a short tail. Boundaries between
segments land on whole seconds; only the two title cards (intro, interstitial) and
the segment edges that touch them are fractional. Whole-second boundaries round up,
so they cost a little spare time: the last segment (the closing question) absorbs what
is left. Fails loudly if the speech cannot fit; shorten the text or raise
"speed" in narration.json and re-render.
"""

import json
import math
from pathlib import Path

TRAILER_DIR = Path(__file__).resolve().parent
REPO_ROOT = TRAILER_DIR.parents[3]
OUTPUT_DIR = TRAILER_DIR / "out"
TOTAL = 60
LEAD, TAIL = 0.2, 0.2

n = json.loads((TRAILER_DIR / "narration.json").read_text())
dur = json.loads((OUTPUT_DIR / "audio" / "durations.json").read_text())

intro, card = n["intro"], n["interstitial"]
card_follows = card.get("followsSegment", "inspect")
card_len = card["duration"]
segments = n["segments"]


def lead(i: int, b: dict) -> float:
    # Only the first segment may start its voice early (voiceStart is absolute time).
    return b["voiceStart"] - intro["end"] if i == 0 and "voiceStart" in b else LEAD


need = [dur[b["id"]] + lead(i, b) + TAIL for i, b in enumerate(segments)]

def layout(extra: int):
    """Place every segment; `extra` whole seconds go to the `extraTimeTo` segment. Returns the last segment's spare time."""
    t = intro["end"]  # earliest time the next segment can start
    for i, b in enumerate(segments):
        b["start"] = round(t, 2)
        earliest_end = t + need[i]
        if i == len(segments) - 1:
            b["end"] = TOTAL
            return TOTAL - earliest_end
        if b["id"] == card_follows:
            # A title card follows: this segment ends exactly when its speech does.
            b["end"] = round(earliest_end, 2)
            card["start"], card["end"] = b["end"], round(b["end"] + card_len, 2)
            t = card["end"]
        else:
            b["end"] = math.ceil(earliest_end - 1e-9) + (extra if b["id"] == extra_time_to else 0)
            t = b["end"]


extra_time_to = n.get("extraTimeTo")
spare = layout(0)
if spare < 0:
    raise SystemExit(
        f"Speech runs {-spare:.1f}s past {TOTAL}s once boundaries are rounded to whole seconds. "
        "Trim about that much speech (or raise speed) and re-render."
    )

if extra_time_to:
    extra = int(spare)  # whole seconds only; the remainder stays with the closing segment
    # Don't slow the segment past real time: the recorded action only lasts so long.
    marks = REPO_ROOT / "ui" / "demo" / "video-output" / "trailer-demo-marks.json"
    if extra_time_to == "upload" and marks.exists():
        m = json.loads(marks.read_text())
        up = next(b for b in segments if b["id"] == "upload")
        extra = min(extra, max(0, math.ceil(m["resultsAtSec"] - m["readyAtSec"] - (up["end"] - up["start"]))))
    spare = layout(extra)

timeline = {
    "total": TOTAL,
    "segments": {b["id"]: {"start": b["start"], "end": b["end"]} for b in segments},
    "interstitial": {"start": card["start"], "end": card["end"]},
}

OUTPUT_DIR.mkdir(exist_ok=True)
(OUTPUT_DIR / "timeline.json").write_text(json.dumps(timeline, indent=2) + "\n")

print(f"{'segment':<10} {'window':<14} speech")
print(f"{'intro':<10} {intro['start']:5.2f} - {intro['end']:5.2f}")
for b in segments:
    print(f"{b['id']:<10} {b['start']:5.2f} - {b['end']:5.2f}  {dur[b['id']]:5.1f}s")
    if b["id"] == card_follows:
        print(f"{'card':<10} {card['start']:5.2f} - {card['end']:5.2f}")

print(f"spare time left in the last segment: {spare:.1f}s")
