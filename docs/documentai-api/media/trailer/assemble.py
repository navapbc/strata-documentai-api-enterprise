"""Stitch the three Playwright clips, overlays, and narration into one ~60s MP4.

Run with:  python3 docs/documentai-api/media/trailer/assemble.py [--no-audio] [--mark-offset 0.5]

Inputs (all produced locally, all gitignored):
  ui/demo/video-output/trailer-demo-*/video.webm            segments 1-2 (+ trailer-demo-marks.json)
  ui/admin/video-output/trailer-admin-rules-*/video.webm    segment 3
  ui/admin/video-output/trailer-admin-metrics-*/video.webm  segment 4
  docs/documentai-api/media/trailer/out/audio/*.wav                              from tts_kokoro.py (optional)

Outputs: docs/documentai-api/media/trailer/out/trailer.mp4 and trailer.srt.

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


def probe(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())


def one(pattern: str) -> str:
    hits = sorted(glob.glob(str(REPO_ROOT / pattern)))
    if not hits:
        sys.exit(f"No clip matches {pattern}. Record first (see README).")
    return hits[-1]


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


def wav_seconds(path: Path) -> float | None:
    if not path.exists():
        return None
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def srt_time(t: float) -> str:
    ms = round(t * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def _card_color() -> str:
    """The title-card background, read from overlays.css so the clips fade into the same color."""
    m = re.search(r"--card-bg:\s*#([0-9a-fA-F]{6})", (TRAILER_DIR / "overlays.css").read_text())
    if not m:
        raise SystemExit("Could not find a '--card-bg: #rrggbb' line in overlays.css")
    return "0x" + m.group(1)


CLIP_FADE_COLOR = _card_color()  # clips fade through the card color instead of hard-cutting
CLIP_FADE_SECS = 0.3


def retime(idx: int, start: float, end: float, target: float,
           fade_in: bool = False, fade_out: bool = False) -> str:
    """Filter for input idx: trim to [start,end], then fit to `target` seconds."""
    dur = end - start
    f = f"[{idx}:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS"
    if dur > target:
        f += f",setpts=PTS*{target / dur:.5f}"
    elif dur < target:
        f += f",tpad=stop_mode=clone:stop_duration={target - dur:.3f}"
    f += f",fps={FPS},scale={W}:{H},format=yuv420p,trim=duration={target:.3f},setpts=PTS-STARTPTS"
    if fade_in:
        f += f",fade=t=in:st=0:d={CLIP_FADE_SECS}:color={CLIP_FADE_COLOR}"
    if fade_out:
        f += f",fade=t=out:st={target - CLIP_FADE_SECS:.3f}:d={CLIP_FADE_SECS}:color={CLIP_FADE_COLOR}"
    return f


def retime_hold(idx: int, start: float, end: float, action_target: float, hold: float,
                fade_in: bool = False) -> str:
    """Hold the frame at `start` for `hold` seconds, then play [start,end] fitted
    to `action_target` seconds. Total length is hold + action_target."""
    dur = end - start
    f = f"[{idx}:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS"
    if dur > action_target:
        f += f",setpts=PTS*{action_target / dur:.5f}"
    elif dur < action_target:
        f += f",tpad=stop_mode=clone:stop_duration={action_target - dur:.3f}"
    f += f",tpad=start_mode=clone:start_duration={hold:.3f}"
    f += f",fps={FPS},scale={W}:{H},format=yuv420p,trim=duration={hold + action_target:.3f},setpts=PTS-STARTPTS"
    if fade_in:
        f += f",fade=t=in:st=0:d={CLIP_FADE_SECS}:color={CLIP_FADE_COLOR}"
    return f


def voice_start(b: dict) -> float:
    """When a segment's voice begins: an explicit voiceStart, else shortly after the segment opens."""
    return b.get("voiceStart", b["start"] + LEAD)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--mark-offset", type=float, default=0.5,
                    help="seconds the video starts before the spec's clock (default 0.5)")
    args = ap.parse_args()

    narration = load_narration()
    segments = {b["id"]: b for b in narration["segments"]}

    demo = one("ui/demo/video-output/trailer-demo-*/video.webm")
    rules = one("ui/admin/video-output/trailer-admin-rules-*/video.webm")
    metrics = one("ui/admin/video-output/trailer-admin-metrics-*/video.webm")
    marks = json.loads((REPO_ROOT / "ui/demo/video-output/trailer-demo-marks.json").read_text())
    results_at = marks["resultsAtSec"] + args.mark_offset
    ready_at = marks["readyAtSec"] + args.mark_offset
    admin_marks = json.loads((REPO_ROOT / "ui/admin/video-output/trailer-admin-marks.json").read_text())
    rules_from = admin_marks["rules"] + args.mark_offset
    metrics_from = admin_marks["metrics"] + args.mark_offset
    demo_len, rules_len, metrics_len = probe(demo), probe(rules), probe(metrics)

    # --- captions: timed across each segment's speech ---------------------------
    cues, srt = [], []
    for b in narration["segments"]:
        vs = voice_start(b)
        audio = None if args.no_audio else wav_seconds(OUTPUT_DIR / "audio" / f"{b['id']}.wav")
        chunks = chunk_sentences(b["text"])
        total_chars = sum(len(c) for c in chunks)
        speech = audio if audio else total_chars / CHARS_PER_SEC
        t = vs
        for c in chunks:
            d = speech * len(c) / total_chars
            cues.append({"start": t, "end": t + d, "lines": wrap(c, MAX_LINE)[:2]})
            t += d
    for i, c in enumerate(cues, 1):
        srt.append(f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n" + "\n".join(c["lines"]).replace("*", "") + "\n")
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "trailer.srt").write_text("\n".join(srt))

    for i, c in enumerate(cues):
        c["file"] = f"cap-{i:02}.png"

    # --- chips: one per listed word, appearing as it is spoken ---------------
    chips = []
    cfg = narration.get("chips")
    if cfg:
        cb = segments[cfg["segment"]]
        audio = None if args.no_audio else wav_seconds(OUTPUT_DIR / "audio" / f"{cb['id']}.wav")
        speech = audio if audio else len(cb["text"]) / CHARS_PER_SEC
        times = word_times(cb["text"], cfg["words"], voice_start(cb), speech)
        for i, w in enumerate(cfg["words"]):
            chips.append({"file": f"chip-{i}.png", "text": w.capitalize(), "index": i,
                          "start": times.get(w, voice_start(cb))})
    spec = {
        "width": W, "height": H,
        "captions": [{"file": c["file"], "lines": c["lines"]} for c in cues],
        "badges": [
            {"file": "badge-compressed.png", "pos": "tr",
             "text": "Edited: processing time compressed"},
            {"file": "badge-synthetic.png", "pos": "tc", "text": "Synthetic data"},
        ],
        "chips": [{"file": c["file"], "text": c["text"], "index": c["index"]} for c in chips],
        "endCard": {"file": "endcard.png", "question": narration["question"],
                    "repoUrl": narration["repoUrl"]},
        "intro": {"file": "intro.png", "title": narration["intro"]["title"],
                  "subtitle": narration["intro"]["subtitle"]},
        "interstitial": {"file": "interstitial.png", "title": narration["interstitial"]["title"],
                         "subtitle": narration["interstitial"]["subtitle"]},
    }
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "overlay-spec.json").write_text(json.dumps(spec, indent=2))
    subprocess.run(["node", str(TRAILER_DIR / "render_overlays.mjs"), str(OUTPUT_DIR / "overlay-spec.json"), str(OVERLAYS_DIR)], check=True)

    # --- video graph ----------------------------------------------------------
    ov, up, insp, conf, mon, ask = (segments[k] for k in ("overview", "upload", "inspect", "configure", "monitor", "ask"))
    seg = lambda b: b["end"] - b["start"]
    inputs = [demo, demo, rules, metrics]
    card = narration["interstitial"]
    intro = narration["intro"]
    card_secs = card["end"] - card["start"]
    intro_secs = intro["end"] - intro["start"]
    graph = [
        # Overview holds the ready upload screen; the real action plays in the upload segment.
        retime_hold(0, ready_at, results_at, seg(up), seg(ov), fade_in=True) + "[a]",
        retime(1, results_at, demo_len, seg(insp), fade_out=True) + "[b]",
        retime(2, rules_from, rules_len, seg(conf), fade_in=True) + "[c]",
        retime(3, metrics_from, metrics_len, seg(mon), fade_out=True) + "[d]",
    ]
    # Still images follow the four clips: end card is input 4, interstitial 5, intro 6.
    n = len(inputs)
    inputs.append(None)
    png_inputs = [("endcard.png", seg(ask)), ("interstitial.png", card_secs), ("intro.png", intro_secs)]
    for i, (_, secs) in enumerate(png_inputs):
        label = "ekl"[i] if i < 3 else str(i)
        graph.append(f"[{n + i}:v]fps={FPS},scale={W}:{H},format=yuv420p,trim=duration={secs:.3f},setpts=PTS-STARTPTS[{label}]")
    graph.append("[l][a][b][k][c][d][e]concat=n=7:v=1:a=0[base]")

    action_speed = (results_at - ready_at) / seg(up)
    print(f"Upload action plays at {action_speed:.2f}x")
    overlays = []
    if action_speed > 1.15:  # label the edit when processing is visibly sped up
        overlays.append(("badge-compressed.png", up["start"] + 0.3, up["end"] - 0.2, False))
    overlays += [("badge-synthetic.png", intro["end"], card["start"], False),
                 ("badge-synthetic.png", card["end"], ask["start"], False)]
    # Chips fade in as spoken and fade out when the upload segment begins.
    overlays += [(c["file"], c["start"], up["start"], True) for c in chips]
    # The end card already shows the question, so skip its caption (the SRT keeps it).
    overlays += [(c["file"], max(c["start"], intro["end"]), c["end"], False)
                 for c in cues if c["start"] < ask["start"] and c["end"] > intro["end"]]

    cmd = ["ffmpeg", "-v", "error", "-y"]
    for p in inputs[:-1]:
        cmd += ["-i", p]
    for name, secs in png_inputs:
        cmd += ["-framerate", str(FPS), "-loop", "1", "-t", f"{secs:.3f}", "-i", str(OVERLAYS_DIR / name)]
    first_overlay = len(inputs) + len(png_inputs) - 1  # `inputs` already counts one placeholder
    for name, *_ in overlays:
        cmd += ["-framerate", str(FPS), "-loop", "1", "-t", "60", "-i", str(OVERLAYS_DIR / name)]
    prev = "base"
    for i, (_, a, b, fx) in enumerate(overlays):
        nxt = f"o{i}"
        src = f"{first_overlay + i}:v"
        if fx:  # fade the image's alpha in at `a` and out before `b`
            graph.append(f"[{src}]format=rgba,fade=t=in:st={a:.3f}:d=0.3:alpha=1,"
                         f"fade=t=out:st={b - 0.25:.3f}:d=0.25:alpha=1[f{i}]")
            src = f"[f{i}]"
        else:
            src = f"[{src}]"
        graph.append(f"[{prev}]{src}overlay=0:0:enable='between(t,{a:.3f},{b:.3f})'[{nxt}]")
        prev = nxt

    out_file = OUTPUT_DIR / "trailer.mp4"
    audio_files = [] if args.no_audio else [(voice_start(b), OUTPUT_DIR / "audio" / f"{b['id']}.wav") for b in narration["segments"]]
    audio_files = [(s, p) for s, p in audio_files if p.exists()]
    a_base = first_overlay + len(overlays)
    for _, p in audio_files:
        cmd += ["-i", str(p)]
    amap = []
    if audio_files:
        for i, (s, _) in enumerate(audio_files):
            graph.append(f"[{a_base + i}:a]adelay={int(s * 1000)}|{int(s * 1000)}[s{i}]")
        graph.append("".join(f"[s{i}]" for i in range(len(audio_files))) +
                     f"amix=inputs={len(audio_files)}:normalize=0,apad,atrim=duration=60[aout]")
        amap = ["-map", "[aout]", "-c:a", "aac", "-b:a", "160k"]
    cmd += ["-filter_complex", ";".join(graph), "-map", f"[{prev}]", *amap,
            "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-movflags", "+faststart", "-t", "60", str(out_file)]
    subprocess.run(cmd, check=True)
    print(f"Wrote {out_file} ({probe(str(out_file)):.1f}s) and trailer.srt"
          f"{'' if audio_files else ' (no audio)'}")


if __name__ == "__main__":
    main()
