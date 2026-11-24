# These are standalone scripts, not a package.
# ruff: noqa: INP001
"""Caption cues: split narration into on-screen captions and write the SRT file."""

from dataclasses import dataclass

from narration import OUTPUT_DIR, Narration
from timing import CHARS_PER_SEC, voice_start, wav_duration

MAX_LINE = 42  # characters per caption line
MAX_CUE = 2 * MAX_LINE  # a cue is at most two lines


@dataclass
class Cue:
    """One on-screen caption: its lines, when it is shown, and the overlay PNG it is drawn to."""

    start: float
    end: float
    lines: list[str]
    file: str = ""


def wrap(text: str, width: int) -> list[str]:
    """Break `text` into lines of at most `width` characters, at word boundaries.

    Fills each line before starting the next; a word longer than `width` stays whole on its line.
    A cue near MAX_CUE can need a third line, which `build_cues` drops (it keeps two).
    """
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()

    if line:
        lines.append(line)

    return lines


def chunk_sentences(text: str) -> list[str]:
    """Split narration text into cue-sized chunks of at most MAX_CUE characters.

    Each sentence is a cue; a longer sentence is split into roughly equal parts,
    preferring a break just after a comma, so no cue is a short orphan.
    """
    sentences, sentence = [], ""
    for word in text.split():
        sentence = f"{sentence} {word}".strip()
        if word.endswith((".", "?", "!")):
            sentences.append(sentence)
            sentence = ""

    if sentence:
        sentences.append(sentence)

    chunks = []
    for sentence in sentences:
        # Split long sentences into equal-ish parts so no cue is a short orphan.
        words = sentence.split()
        parts = -(-len(sentence) // MAX_CUE)
        start = 0
        for remaining_parts in range(parts, 1, -1):
            # Break near an even split, preferring just after a comma.
            ideal_size = len(" ".join(words[start:])) / remaining_parts
            best_break, best_score = None, None
            for i in range(start + 1, len(words) - (remaining_parts - 1) + 1):
                size = len(" ".join(words[start:i]))
                if size > MAX_CUE:
                    break
                score = abs(size - ideal_size) - (12 if words[i - 1].endswith(",") else 0)
                if best_score is None or score < best_score:
                    best_break, best_score = i, score
            chunks.append(" ".join(words[start:best_break]))
            start = best_break
        chunks.append(" ".join(words[start:]))
    return chunks


def srt_time(t: float) -> str:
    """Format seconds as an SRT timestamp, HH:MM:SS,mmm."""
    ms = round(t * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def build_cues(narration: Narration, no_audio: bool) -> list[Cue]:
    """Build timed caption cues from narration segments, write the SRT file, and return the cues.

    A segment's speech time (the measured WAV, or an estimate with `no_audio`) is shared out
    among its cues by character count, starting when the segment's voice starts. The SRT drops
    the `*` emphasis marks; the cues keep them so the overlay can show the word in bold.
    """
    cues: list[Cue] = []
    for segment in narration.segments:
        audio_secs = None if no_audio else wav_duration(OUTPUT_DIR / "audio" / f"{segment.id}.wav")
        chunks = chunk_sentences(segment.text)
        total_chars = sum(len(chunk) for chunk in chunks)
        speech_secs = audio_secs or total_chars / CHARS_PER_SEC
        cue_start = voice_start(segment)
        for chunk in chunks:
            cue_secs = speech_secs * len(chunk) / total_chars
            cues.append(
                Cue(start=cue_start, end=cue_start + cue_secs, lines=wrap(chunk, MAX_LINE)[:2])
            )
            cue_start += cue_secs

    srt = [
        f"{i}\n{srt_time(cue.start)} --> {srt_time(cue.end)}\n"
        + "\n".join(cue.lines).replace("*", "")
        + "\n"
        for i, cue in enumerate(cues, 1)
    ]

    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "documentai-trailer.srt").write_text("\n".join(srt))
    for i, cue in enumerate(cues):
        cue.file = f"cap-{i:02}.png"
    return cues
