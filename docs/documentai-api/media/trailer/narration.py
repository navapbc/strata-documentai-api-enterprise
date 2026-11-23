"""Load narration.json merged with the generated timeline (out/timeline.json)."""

import json
from pathlib import Path

TRAILER_DIR = Path(__file__).resolve().parent
REPO_ROOT = TRAILER_DIR.parents[3]
OUTPUT_DIR = TRAILER_DIR / "out"
TIMELINE = OUTPUT_DIR / "timeline.json"


def load() -> dict:
    n = json.loads((TRAILER_DIR / "narration.json").read_text())
    if not TIMELINE.exists():
        raise SystemExit(
            f"{TIMELINE.relative_to(REPO_ROOT)} not found. Run a full build once "
            "(make trailer) so the voiceover is measured and the timeline is built."
        )
    timeline = json.loads(TIMELINE.read_text())
    for b in n["segments"]:
        b.update(timeline["segments"][b["id"]])
    n["total"] = timeline["total"]
    n["interstitial"].update(timeline["interstitial"])
    return n
