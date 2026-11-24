"""When things happen: voice start times, spoken-word estimates, and the chips and
callouts that appear as their words are spoken."""

import wave
from dataclasses import dataclass
from pathlib import Path

from narration import OUTPUT_DIR, Narration, Segment

LEAD = 0.2  # seconds between a segment opening and its voice starting (matches timeline.py)
CHARS_PER_SEC = 15.0  # fallback speech-rate estimate when there is no audio yet
CALLOUT_LEAD = 0.3  # a callout appears this long before its word is spoken


@dataclass
class Chip:
    file: str
    text: str
    index: int
    start: float


@dataclass
class Callout:
    file: str
    start: float


def word_times(text: str, words: list[str], start: float, speech_secs: float) -> dict[str, float]:
    """Estimate when each of `words` is spoken, given the voice starts at `start` and speaks for `speech_secs`.
    Each word's time is its position in the text, weighted by length, with extra weight for pauses on punctuation."""
    tokens = text.split()
    weights = [len(t) + 1 + (4 if t.endswith(",") else 6 if t.endswith((".", "?", "!")) else 0) for t in tokens]
    total_weight, weight_before, times = sum(weights), 0, {}
    for token, weight in zip(tokens, weights):
        word = token.strip(",.?!*").lower()
        if word in words and word not in times:
            times[word] = start + speech_secs * weight_before / total_weight
        weight_before += weight

    return times


def wav_duration(path: Path) -> float | None:
    """Return the duration in seconds of a WAV file, or None if it doesn't exist."""
    if not path.exists():
        return None
    
    with wave.open(str(path)) as wav:
        return wav.getnframes() / wav.getframerate()


def voice_start(segment: Segment) -> float:
    """When a segment's voice begins: an explicit voice_start, else shortly after the segment opens."""
    return segment.voice_start if segment.voice_start is not None else segment.start + LEAD


def spoken_word_times(segment: Segment, words: list[str], no_audio: bool) -> dict[str, float]:
    """When each of `words` is spoken in `segment` (estimated from the measured speech length)."""
    audio_secs = None if no_audio else wav_duration(OUTPUT_DIR / "audio" / f"{segment.id}.wav")
    speech_secs = audio_secs if audio_secs else len(segment.text) / CHARS_PER_SEC
    return word_times(segment.text, words, voice_start(segment), speech_secs)


def build_chips(narration: Narration, no_audio: bool) -> list[Chip]:
    """Build keyword chips timed to when each word is spoken in its segment."""
    chip_config = narration.chips
    if not chip_config:
        return []
    segment = narration.segment(chip_config["segment"])
    times = spoken_word_times(segment, chip_config["words"], no_audio)
    return [
        Chip(file=f"chip-{i}.png", text=word.capitalize(), index=i, start=times.get(word, voice_start(segment)))
        for i, word in enumerate(chip_config["words"])
    ]


def build_callouts(narration: Narration, no_audio: bool) -> list[Callout]:
    """The blurry-upload and portal callouts, each appearing just before its word is spoken."""
    callout_config = narration.callouts
    if not callout_config:
        return []
    segment = narration.segment(callout_config["segment"])
    times = spoken_word_times(segment, callout_config["words"], no_audio)
    files = ("callout-design.png", "callout-blur.png", "callout-portal.png")
    return [
        Callout(file=file, start=max(segment.start, times.get(word, voice_start(segment)) - CALLOUT_LEAD))
        for file, word in zip(files, callout_config["words"])
    ]
