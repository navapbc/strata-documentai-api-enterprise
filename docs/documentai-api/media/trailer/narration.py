"""Load narration.json (hand-written content) and, optionally, the generated timeline (out/timeline.json)."""

import json
from dataclasses import dataclass
from pathlib import Path

TRAILER_DIR = Path(__file__).resolve().parent
REPO_ROOT = TRAILER_DIR.parents[3]
OUTPUT_DIR = TRAILER_DIR / "out"
TIMELINE = OUTPUT_DIR / "timeline.json"


@dataclass
class Segment:
    """One narrated stretch of the video. `start` and `end` come from the timeline."""

    id: str
    text: str
    voice_start: float | None = None  # absolute time the voice starts, if not just after the segment opens
    start: float = 0.0
    end: float = 0.0

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class Card:
    """A title card (the intro, or the one between the two halves of the video)."""

    title: str
    subtitle: str
    start: float = 0.0
    end: float = 0.0
    show_secs: float | None = None  # how long the card is shown (the interstitial)
    follows_segment: str | None = None  # the segment the card comes after (the interstitial)

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class Narration:
    voice: str
    speed: float
    emphasis: str
    question: str
    repo_url: str
    intro: Card
    interstitial: Card
    segments: list[Segment]
    chips: dict | None  # {segment, words}: chips shown as each word is spoken
    callouts: dict | None  # {segment, words, design, blur, portal}: the integrate panels
    extra_time_to: str | None  # the segment that gets the spare whole seconds
    total: float = 0.0  # the video length, from the timeline

    def segment(self, segment_id: str) -> Segment:
        return next(s for s in self.segments if s.id == segment_id)


def _card(d: dict) -> Card:
    return Card(
        title=d["title"],
        subtitle=d["subtitle"],
        start=d.get("start", 0.0),
        end=d.get("end", 0.0),
        show_secs=d.get("duration"),
        follows_segment=d.get("followsSegment"),
    )


def load_content() -> Narration:
    """Only what is in narration.json: no timeline yet, so segment and card times are 0."""
    n = json.loads((TRAILER_DIR / "narration.json").read_text())
    return Narration(
        voice=n.get("voice", "af_heart"),
        speed=n.get("speed", 1.0),
        emphasis=n.get("emphasis", "none"),
        question=n["question"],
        repo_url=n["repoUrl"],
        intro=_card(n["intro"]),
        interstitial=_card(n["interstitial"]),
        segments=[Segment(id=s["id"], text=s["text"], voice_start=s.get("voiceStart")) for s in n["segments"]],
        chips=n.get("chips"),
        callouts=n.get("callouts"),
        extra_time_to=n.get("extraTimeTo"),
    )


def load() -> Narration:
    """narration.json merged with the generated timeline (out/timeline.json)."""
    n = load_content()
    if not TIMELINE.exists():
        raise SystemExit(
            f"{TIMELINE.relative_to(REPO_ROOT)} not found. Run a full build once "
            "(make trailer) so the voiceover is measured and the timeline is built."
        )
    
    timeline = json.loads(TIMELINE.read_text())
    for s in n.segments:
        s.start, s.end = timeline["segments"][s.id]["start"], timeline["segments"][s.id]["end"]
    
    n.interstitial.start, n.interstitial.end = timeline["interstitial"]["start"], timeline["interstitial"]["end"]
    n.total = timeline["total"]
    return n
