"""Stitch the three Playwright clips, overlays, and narration into one MP4.

Run with:  python3 docs/documentai-api/media/trailer/assemble.py [--no-audio] [--mark-offset 0.5]

Inputs (all produced locally, all gitignored):
  ui/demo/video-output/trailer-demo-*/video.webm            segments 1-2 (+ trailer-demo-marks.json)
  ui/admin/video-output/trailer-admin-rules-*/video.webm    segment 3
  ui/admin/video-output/trailer-admin-metrics-*/video.webm  segment 4
  docs/documentai-api/media/trailer/out/audio/*.wav                              from tts_kokoro.py (optional)

Outputs: docs/documentai-api/media/trailer/out/documentai-trailer.mp4 and documentai-trailer.srt.

Each clip is retimed to its segment window: sped up when longer, last frame held
when shorter. The upload+processing half of clip 1 is the part that gets sped
up, and the video labels it as compressed. Standard library only.
"""

import argparse
import glob
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Self
import wave
from pathlib import Path

from narration import load as load_narration



TRAILER_DIR = Path(__file__).resolve().parent
REPO_ROOT = TRAILER_DIR.parents[3]  # repo root (docs/documentai-api/media/trailer -> up four)
OUTPUT_DIR = TRAILER_DIR / "out"
OVERLAYS_DIR = OUTPUT_DIR / "overlays"
W, H, FPS = 1280, 800, 25
LEAD = 0.2  # seconds between a segment opening and its voice starting (matches timeline.py)
CHARS_PER_SEC = 15.0  # fallback speech-rate estimate when there is no audio yet
MAX_LINE = 42
MAX_CUE = 84
CLIP_FADE_SECS = 0.3
INTRO_LOGO_FADE_IN, INTRO_LOGO_FADE_OUT = 0.5, 0.4  # the intro logo's fades
INTRO_LOGO_SECS = 1.6  # the intro logo is on screen this long, including its fades
INTRO_TITLE_AT = 1.5  # the title fades in as the voice starts (narration.json voiceStart)
FADE_IN_SECS = 0.5  # how long the intro title and subtitle, and the end logo, take to fade in
INTRO_STAGGER = 0.7  # the subtitle fades in as the voice reaches "open-source"
CALLOUT_LEAD = 0.3  # a callout appears this long before its word is spoken
END_LOGO_BEFORE_END = 1.6  # the end-card logo starts fading in this long before the video ends

@dataclass
class Cue:
    start: float
    end: float
    lines: list[str]
    file: str = ""


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


@dataclass
class StillInput:
    name: str
    duration: float
    label: str


@dataclass
class Overlay:
    file: str
    start: float
    end: float
    fade_in: bool = False
    fade_out: bool = False
    fade_in_dur: float = CLIP_FADE_SECS
    fade_out_dur: float = 0.25


def _card_color() -> str:
    """The title-card background, read from overlays.css so the clips fade into the same color."""
    m = re.search(r"--card-bg:\s*#([0-9a-fA-F]{6})", (TRAILER_DIR / "overlays.css").read_text())
    if not m:
        raise SystemExit("Could not find a '--card-bg: #rrggbb' line in overlays.css")
    return "0x" + m.group(1)


CLIP_FADE_COLOR = _card_color()  # clips fade through the card color instead of hard-cutting

def clip_duration(path: str) -> float:
    """Return the duration in seconds of a video file by calling ffprobe."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())


def latest_recording(pattern: str) -> str:
    """Return the most recently recorded clip matching a glob pattern.
    Directories are timestamped so the last entry alphabetically is the newest.
    """
    matches = sorted(glob.glob(str(REPO_ROOT / pattern)))
    if not matches:
        sys.exit(f"No clip matches {pattern}. Record first (see README).")
    return matches[-1]


def wrap(text: str, width: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        lines.append(cur)
    return lines


def chunk_sentences(text: str) -> list[str]:
    """Split into cues of at most two short lines, preferring sentence breaks."""
    sentences, cur = [], ""
    for word in text.split():
        cur = f"{cur} {word}".strip()
        if word.endswith((".", "?", "!")):
            sentences.append(cur)
            cur = ""
    if cur:
        sentences.append(cur)
    cues = []
    for s in sentences:
        # Split long sentences into equal-ish parts so no cue is a short orphan.
        words = s.split()
        parts = -(-len(s) // MAX_CUE)
        start = 0
        for p in range(parts, 1, -1):
            # Break near an even split, preferring just after a comma.
            ideal = len(" ".join(words[start:])) / p
            best, best_score = None, None
            for i in range(start + 1, len(words) - (p - 1) + 1):
                size = len(" ".join(words[start:i]))
                if size > MAX_CUE:
                    break
                score = abs(size - ideal) - (12 if words[i - 1].endswith(",") else 0)
                if best_score is None or score < best_score:
                    best, best_score = i, score
            cues.append(" ".join(words[start:best]))
            start = best
        cues.append(" ".join(words[start:]))
    return cues


def word_times(text: str, words: list[str], voice_start: float, speech: float) -> dict[str, float]:
    """Estimate when each word is spoken: position in the text, with pause weight on punctuation."""
    toks = text.split()
    weights = [len(w) + 1 + (4 if w.endswith(",") else 6 if w.endswith((".", "?", "!")) else 0) for w in toks]
    total, cum, out = sum(weights), 0, {}
    for w, wt in zip(toks, weights):
        key = w.strip(",.?!*").lower()
        if key in words and key not in out:
            out[key] = voice_start + speech * cum / total
        cum += wt
    return out


def wav_duration(path: Path) -> float | None:
    """Return the duration in seconds of a WAV file, or None if it doesn't exist."""
    if not path.exists():
        return None
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def srt_time(t: float) -> str:
    ms = round(t * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"





class ClipFilter:
    """Builds an ffmpeg video filter chain for a single input clip."""

    def __init__(self, idx: int, start: float, end: float) -> None:
        self._parts = [f"[{idx}:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS"]
        self._dur = end - start
        self._total: float | None = None

    @classmethod
    def still(cls, idx: int, secs: float) -> Self:
        """For a looped still-image input: just normalize to `secs` duration."""
        obj = object.__new__(cls)
        obj._parts = [f"[{idx}:v]null"]  # a first filter, so later parts can be comma-joined
        obj._dur = secs
        obj._total = secs
        return obj

    def fit(self, target: float) -> Self:
        """Speed up or pad to exactly `target` seconds."""
        if self._dur > target:
            self._parts.append(f"setpts=PTS*{target / self._dur:.5f}")
        elif self._dur < target:
            self._parts.append(f"tpad=stop_mode=clone:stop_duration={target - self._dur:.3f}")
        self._total = target
        return self

    def hold_start(self, hold: float) -> Self:
        """Prepend a freeze-frame of duration `hold` before the clip action."""
        self._parts.append(f"tpad=start_mode=clone:start_duration={hold:.3f}")
        if self._total is not None:
            self._total += hold
        return self

    def normalize(self, total: float | None = None) -> Self:
        """Enforce fps/scale/pixel-format and hard-trim to the final duration."""
        dur = total or self._total or self._dur
        self._parts.append(
            f"fps={FPS},scale={W}:{H},format=yuv420p,trim=duration={dur:.3f},setpts=PTS-STARTPTS"
        )
        return self

    def fade_in(self, d: float = CLIP_FADE_SECS) -> Self:
        self._parts.append(f"fade=t=in:st=0:d={d}:color={CLIP_FADE_COLOR}")
        return self

    def fade_out(self, d: float = CLIP_FADE_SECS) -> Self:
        st = (self._total or self._dur) - d
        self._parts.append(f"fade=t=out:st={st:.3f}:d={d}:color={CLIP_FADE_COLOR}")
        return self

    def label(self, lbl: str) -> str:
        return ",".join(self._parts) + f"[{lbl}]"

    def __str__(self) -> str:
        return ",".join(self._parts)


def retime(idx: int, start: float, end: float, target: float,
           fade_in: bool = False, fade_out: bool = False) -> ClipFilter:
    """Trim [start,end] from input idx and fit to `target` seconds."""
    f = ClipFilter(idx, start, end).fit(target).normalize()
    if fade_in:
        f.fade_in()
    if fade_out:
        f.fade_out()
    return f


def retime_hold(idx: int, start: float, end: float, action_target: float, hold: float,
                fade_in: bool = False) -> ClipFilter:
    """Freeze `hold` seconds, then play [start,end] fitted to `action_target` seconds."""
    f = ClipFilter(idx, start, end).fit(action_target).hold_start(hold).normalize()
    if fade_in:
        f.fade_in()
    return f


def _overlay_filter(src: str, lbl: str, overlay: Overlay) -> list[str]:
    """Return filter graph lines that apply alpha fades to an overlay input.
    Returns an empty list when no fades are needed."""
    if not overlay.fade_in and not overlay.fade_out:
        return []
    parts = f"[{src}]format=rgba"
    if overlay.fade_in:
        parts += f",fade=t=in:st={overlay.start:.3f}:d={overlay.fade_in_dur}:alpha=1"
    if overlay.fade_out:
        parts += f",fade=t=out:st={overlay.end - overlay.fade_out_dur:.3f}:d={overlay.fade_out_dur}:alpha=1"
    return [parts + f"[{lbl}]"]


def segment_duration(segment: dict) -> float:
    return segment["end"] - segment["start"]


def voice_start(segment: dict) -> float:
    """When a segment's voice begins: an explicit voiceStart, else shortly after the segment opens."""
    return segment.get("voiceStart", segment["start"] + LEAD)


def build_cues(narration: dict, no_audio: bool) -> list[Cue]:
    """Build timed caption cues from narration segments, write the SRT file, and return the cues."""
    cues: list[Cue] = []
    for b in narration["segments"]:
        audio = None if no_audio else wav_duration(OUTPUT_DIR / "audio" / f"{b['id']}.wav")
        chunks = chunk_sentences(b["text"])
        total_chars = sum(len(c) for c in chunks)
        speech = audio if audio else total_chars / CHARS_PER_SEC
        t = voice_start(b)
        for c in chunks:
            d = speech * len(c) / total_chars
            cues.append(Cue(start=t, end=t + d, lines=wrap(c, MAX_LINE)[:2]))
            t += d
    srt = [
        f"{i}\n{srt_time(c.start)} --> {srt_time(c.end)}\n" + "\n".join(c.lines).replace("*", "") + "\n"
        for i, c in enumerate(cues, 1)
    ]
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "documentai-trailer.srt").write_text("\n".join(srt))
    for i, c in enumerate(cues):
        c.file = f"cap-{i:02}.png"
    return cues


def spoken_word_times(segment: dict, words: list[str], no_audio: bool) -> dict[str, float]:
    """When each of `words` is spoken in `segment` (estimated from the measured speech length)."""
    audio = None if no_audio else wav_duration(OUTPUT_DIR / "audio" / f"{segment['id']}.wav")
    speech = audio if audio else len(segment["text"]) / CHARS_PER_SEC
    return word_times(segment["text"], words, voice_start(segment), speech)


def build_chips(narration: dict, segments: dict, no_audio: bool) -> list[Chip]:
    """Build keyword chips timed to when each word is spoken in its segment."""
    cfg = narration.get("chips")
    if not cfg:
        return []
    cb = segments[cfg["segment"]]
    times = spoken_word_times(cb, cfg["words"], no_audio)
    return [
        Chip(file=f"chip-{i}.png", text=w.capitalize(), index=i, start=times.get(w, voice_start(cb)))
        for i, w in enumerate(cfg["words"])
    ]


def build_callouts(narration: dict, segments: dict, no_audio: bool) -> list[Callout]:
    """The blurry-upload and portal callouts, each appearing just before its word is spoken."""
    cfg = narration.get("callouts")
    if not cfg:
        return []
    cb = segments[cfg["segment"]]
    times = spoken_word_times(cb, cfg["words"], no_audio)
    files = ("callout-design.png", "callout-blur.png", "callout-portal.png")
    return [
        Callout(file=f, start=max(cb["start"], times.get(w, voice_start(cb)) - CALLOUT_LEAD))
        for f, w in zip(files, cfg["words"])
    ]


def render_overlays(narration: dict, cues: list[Cue], chips: list[Chip]) -> None:
    """Write overlay-spec.json and call render_overlays.mjs to produce the overlay PNGs."""
    spec = {
        "width": W, "height": H,
        "captions": [{"file": c.file, "lines": c.lines} for c in cues],
        "badges": [
            {"file": "badge-compressed.png", "pos": "tr", "text": "Edited: processing time compressed"},
            {"file": "badge-synthetic.png", "pos": "tc", "text": "Synthetic data"},
        ],
        "chips": [{"file": c.file, "text": c.text, "index": c.index} for c in chips],
        "callouts": narration.get("callouts"),
        "endCard": {"file": "endcard.png", "question": narration["question"], "repoUrl": narration["repoUrl"]},
        "intro": {"file": "intro.png", "title": narration["intro"]["title"], "subtitle": narration["intro"]["subtitle"]},
        "interstitial": {"file": "interstitial.png", "title": narration["interstitial"]["title"],
                         "subtitle": narration["interstitial"]["subtitle"]},
    }
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "overlay-spec.json").write_text(json.dumps(spec, indent=2))
    subprocess.run(
        ["node", str(TRAILER_DIR / "render_overlays.mjs"), str(OUTPUT_DIR / "overlay-spec.json"), str(OVERLAYS_DIR)],
        check=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--mark-offset", type=float, default=0.5,
                    help="seconds the video starts before the spec's clock (default 0.5)")
    args = ap.parse_args()

    narration = load_narration()
    segments = {b["id"]: b for b in narration["segments"]}

    demo = latest_recording("ui/demo/video-output/trailer-demo-*/video.webm")
    rules = latest_recording("ui/admin/video-output/trailer-admin-rules-*/video.webm")
    metrics = latest_recording("ui/admin/video-output/trailer-admin-metrics-*/video.webm")
    marks = json.loads((REPO_ROOT / "ui/demo/video-output/trailer-demo-marks.json").read_text())
    results_at = marks["resultsAtSec"] + args.mark_offset
    ready_at = marks["readyAtSec"] + args.mark_offset
    admin_marks = json.loads((REPO_ROOT / "ui/admin/video-output/trailer-admin-marks.json").read_text())
    rules_from = admin_marks["rules"] + args.mark_offset
    metrics_from = admin_marks["metrics"] + args.mark_offset
    demo_len, rules_len, metrics_len = clip_duration(demo), clip_duration(rules), clip_duration(metrics)

    cues = build_cues(narration, args.no_audio)
    chips = build_chips(narration, segments, args.no_audio)
    callouts = build_callouts(narration, segments, args.no_audio)
    render_overlays(narration, cues, chips)

    # --- video graph ----------------------------------------------------------
    total = narration["total"]
    ov, up, insp, integ, conf, mon, ask = (
        segments[k] for k in ("overview", "upload", "inspect", "integrate", "configure", "monitor", "ask")
    )
    video_inputs = [demo, demo, rules, metrics]
    card = narration["interstitial"]
    intro = narration["intro"]
    # Still-image inputs appended after the video clips: endcard=4, interstitial=5, intro=6.
    # Labels e/k/l map to their positions in the concat filter: [l][a][b][k][c][d][e].
    still_inputs = [
        StillInput("endcard.png",      segment_duration(ask),  "e"),
        StillInput("interstitial.png", segment_duration(card),  "k"),
        StillInput("intro.png",        segment_duration(intro), "l"),
    ]
    first_still_idx = len(video_inputs)
    graph = [
        retime_hold(0, ready_at, results_at, segment_duration(up), segment_duration(ov), fade_in=True).label("a"),
        retime(1, results_at, demo_len, segment_duration(insp) + segment_duration(integ), fade_out=True).label("b"),
        retime(2, rules_from, rules_len, segment_duration(conf), fade_in=True).label("c"),
        retime(3, metrics_from, metrics_len, segment_duration(mon), fade_out=True).label("d"),
    ]
    for i, still in enumerate(still_inputs):
        graph.append(ClipFilter.still(first_still_idx + i, still.duration).normalize().label(still.label))
    graph.append("[l][a][b][k][c][d][e]concat=n=7:v=1:a=0[base]")

    action_speed = (results_at - ready_at) / segment_duration(up)
    print(f"Upload action plays at {action_speed:.2f}x")
    overlays: list[Overlay] = []
    if action_speed > 1.15:  # label the edit when processing is visibly sped up
        overlays.append(Overlay("badge-compressed.png", up["start"] + 0.3, up["end"] - 0.2))
    overlays += [
        Overlay("badge-synthetic.png", intro["end"], card["start"]),
        Overlay("badge-synthetic.png", card["end"], ask["start"]),
    ]
    # Chips fade in as spoken and fade out when the upload segment begins.
    overlays += [Overlay(c.file, c.start, up["start"], fade_in=True, fade_out=True) for c in chips]
    # Integrate: the results screen dims when the segment's voice starts, and each callout fades in
    # as its example is spoken. They all fade out together when the segment ends.
    if callouts:
        overlays.append(Overlay("backdrop.png", voice_start(integ), integ["end"], fade_in=True, fade_out=True))
        overlays += [Overlay(c.file, c.start, integ["end"], fade_in=True, fade_out=True) for c in callouts]
    # Intro: the logo fades in and out alone, then the title and subtitle fade in.
    overlays += [
        Overlay("intro-logo.png", intro["start"], intro["start"] + INTRO_LOGO_SECS,
                fade_in=True, fade_out=True, fade_in_dur=INTRO_LOGO_FADE_IN, fade_out_dur=INTRO_LOGO_FADE_OUT),
        Overlay("intro-title.png", intro["start"] + INTRO_TITLE_AT, intro["end"],
                fade_in=True, fade_in_dur=FADE_IN_SECS),
        Overlay("intro-subtitle.png", intro["start"] + INTRO_TITLE_AT + INTRO_STAGGER, intro["end"],
                fade_in=True, fade_in_dur=FADE_IN_SECS),
    ]
    # End card: the logo fades in as the voice finishes the question.
    overlays.append(Overlay("endcard-logo.png", ask["end"] - END_LOGO_BEFORE_END, ask["end"],
                            fade_in=True, fade_in_dur=FADE_IN_SECS))
    # The intro card shows the same words the voice opens with, so captions start after it.
    # The end card already shows the question, so skip its caption (the SRT keeps it).
    overlays += [Overlay(c.file, max(c.start, intro["end"]), c.end)
                 for c in cues if c.start < ask["start"] and c.end > intro["end"]]

    cmd = ["ffmpeg", "-v", "error", "-y"]
    for p in video_inputs:
        cmd += ["-i", p]
    for still in still_inputs:
        cmd += ["-framerate", str(FPS), "-loop", "1", "-t", f"{still.duration:.3f}", "-i", str(OVERLAYS_DIR / still.name)]
    first_overlay_idx = len(video_inputs) + len(still_inputs)
    for overlay in overlays:
        cmd += ["-framerate", str(FPS), "-loop", "1", "-t", str(total), "-i", str(OVERLAYS_DIR / overlay.file)]
    current_label = "base"
    for i, overlay in enumerate(overlays):
        next_label = f"o{i}"
        src = f"{first_overlay_idx + i}:v"
        fade_lines = _overlay_filter(src, f"f{i}", overlay)
        graph.extend(fade_lines)
        src = f"[f{i}]" if fade_lines else f"[{src}]"
        graph.append(f"[{current_label}]{src}overlay=0:0:enable='between(t,{overlay.start:.3f},{overlay.end:.3f})'[{next_label}]")
        current_label = next_label

    out_file = OUTPUT_DIR / "documentai-trailer.mp4"
    audio_files = [] if args.no_audio else [(voice_start(b), OUTPUT_DIR / "audio" / f"{b['id']}.wav") for b in narration["segments"]]
    audio_files = [(s, p) for s, p in audio_files if p.exists()]
    first_audio_idx = first_overlay_idx + len(overlays)
    for _, p in audio_files:
        cmd += ["-i", str(p)]
    amap = []
    if audio_files:
        for i, (start, _) in enumerate(audio_files):
            delay_ms = int(start * 1000)
            graph.append(f"[{first_audio_idx + i}:a]adelay={delay_ms}|{delay_ms}[s{i}]")
        graph.append("".join(f"[s{i}]" for i in range(len(audio_files))) +
                     f"amix=inputs={len(audio_files)}:normalize=0,apad,atrim=duration={total}[aout]")
        amap = ["-map", "[aout]", "-c:a", "aac", "-b:a", "160k"]
    cmd += ["-filter_complex", ";".join(graph), "-map", f"[{current_label}]", *amap,
            "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-movflags", "+faststart", "-t", str(total), str(out_file)]
    subprocess.run(cmd, check=True)
    print(f"Wrote {out_file} ({clip_duration(str(out_file)):.1f}s) and documentai-trailer.srt"
          f"{'' if audio_files else ' (no audio)'}")



if __name__ == "__main__":
    main()
