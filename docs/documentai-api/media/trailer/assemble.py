# These are standalone scripts, not a package.
# ruff: noqa: INP001
"""Stitch the three Playwright clips, overlays, and narration into one MP4.

Run with:  python3 docs/documentai-api/media/trailer/assemble.py [--no-audio] [--mark-offset 0.5]

Inputs (all produced locally, all gitignored):
  ui/demo/video-output/trailer-demo-*/video.webm            segments 1-2 (+ trailer-demo-marks.json)
  ui/admin/video-output/trailer-admin-rules-*/video.webm    segment 3
  ui/admin/video-output/trailer-admin-metrics-*/video.webm  segment 4
  docs/documentai-api/media/trailer/out/audio/*.wav                from tts_kokoro.py (optional)

Outputs: docs/documentai-api/media/trailer/out/documentai-trailer.mp4 and documentai-trailer.srt.

Each clip is retimed to its segment window: sped up when longer, last frame held
when shorter. The upload+processing half of clip 1 is the part that gets sped
up, and the video labels it as compressed. Standard library only.
"""

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from captions import Cue, build_cues
from clips import FPS, ClipEdit, Clips, Cut, H, W, clip_duration, find_clips
from narration import OUTPUT_DIR, TRAILER_DIR, Narration
from narration import load as load_narration
from overlay import Overlay
from timing import Callout, Chip, build_callouts, build_chips, voice_start

OVERLAYS_DIR = OUTPUT_DIR / "overlays"
INTRO_LOGO_FADE_IN, INTRO_LOGO_FADE_OUT = 0.5, 0.4  # the intro logo's fades
INTRO_LOGO_SECS = 1.6  # the intro logo is on screen this long, including its fades
INTRO_TITLE_AT = 1.5  # the title fades in as the voice starts (narration.json voiceStart)
FADE_IN_SECS = 0.5  # how long the intro title and subtitle, and the end logo, take to fade in
INTRO_STAGGER = 0.7  # the subtitle fades in as the voice reaches "open-source"
END_LOGO_BEFORE_END = 1.6  # the end-card logo starts fading in this long before the video ends


@dataclass
class StillInput:
    name: str
    duration: float
    label: str


def render_overlays(narration: Narration, cues: list[Cue], chips: list[Chip]) -> None:
    """Write overlay-spec.json and call render_overlays.mjs to produce the overlay PNGs."""
    spec = {
        "width": W,
        "height": H,
        "captions": [{"file": c.file, "lines": c.lines} for c in cues],
        "badges": [
            {
                "file": "badge-compressed.png",
                "pos": "tr",
                "text": "Edited: processing time compressed",
            },
            {"file": "badge-synthetic.png", "pos": "tc", "text": "Synthetic data"},
        ],
        "chips": [{"file": c.file, "text": c.text, "index": c.index} for c in chips],
        "callouts": narration.callouts,
        "endCard": {
            "file": "endcard.png",
            "question": narration.question,
            "repoUrl": narration.repo_url,
        },
        "intro": {
            "file": "intro.png",
            "title": narration.intro.title,
            "subtitle": narration.intro.subtitle,
        },
        "interstitial": {
            "file": "interstitial.png",
            "title": narration.interstitial.title,
            "subtitle": narration.interstitial.subtitle,
        },
    }

    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "overlay-spec.json").write_text(json.dumps(spec, indent=2))
    subprocess.run(
        [
            "node",
            str(TRAILER_DIR / "render_overlays.mjs"),
            str(OUTPUT_DIR / "overlay-spec.json"),
            str(OVERLAYS_DIR),
        ],
        check=True,
    )


def build_video_graph(
    clips: Clips, narration: Narration
) -> tuple[list[str], list[StillInput], list[str]]:
    """The video and still inputs, and the filter lines that fit each to its window, then concat."""
    ov, up, insp, integ, conf, mon, ask = (
        narration.segment(k)
        for k in ("overview", "upload", "inspect", "integrate", "configure", "monitor", "ask")
    )
    card, intro = narration.interstitial, narration.intro
    demo, rules, metrics = clips.demo, clips.rules, clips.metrics
    cuts = [
        Cut(demo, demo.markers["ready"], demo.markers["results"]),  # overview, upload
        Cut(demo, demo.markers["results"], demo.length),  # inspect, integrate
        Cut(rules, rules.markers["start"], rules.length),  # configure
        Cut(metrics, metrics.markers["start"], metrics.length),  # monitor
    ]

    video_inputs = [cut.recording.path for cut in cuts]  # the demo is listed twice, once per cut
    edits = [ClipEdit(i, cut.start, cut.end) for i, cut in enumerate(cuts)]

    # Still-image inputs follow the video clips: endcard=4, interstitial=5, intro=6.
    # Labels e/k/l map to their positions in the concat filter: [l][a][b][k][c][d][e].
    still_inputs = [
        StillInput("endcard.png", ask.duration, "e"),
        StillInput("interstitial.png", card.duration, "k"),
        StillInput("intro.png", intro.duration, "l"),
    ]
    graph = [
        edits[0]
        .fit_to_duration(up.duration)
        .hold_start(ov.duration)
        .normalize()
        .fade_in()
        .label("a"),
        edits[1].fit_to_duration(insp.duration + integ.duration).normalize().fade_out().label("b"),
        edits[2].fit_to_duration(conf.duration).normalize().fade_in().label("c"),
        edits[3].fit_to_duration(mon.duration).normalize().fade_out().label("d"),
    ]

    for i, still in enumerate(still_inputs):
        graph.append(
            ClipEdit.still(len(video_inputs) + i, still.duration).normalize().label(still.label)
        )

    graph.append("[l][a][b][k][c][d][e]concat=n=7:v=1:a=0[base]")
    return video_inputs, still_inputs, graph


def build_overlays(
    narration: Narration,
    cues: list[Cue],
    chips: list[Chip],
    callouts: list[Callout],
    action_speed: float,
) -> list[Overlay]:
    """Every overlay with the time window it is shown in, bottom to top."""
    up, integ, ask = (narration.segment(k) for k in ("upload", "integrate", "ask"))
    card, intro = narration.interstitial, narration.intro
    overlays: list[Overlay] = []
    if action_speed > 1.15:  # label the edit when processing is visibly sped up
        overlays.append(Overlay("badge-compressed.png", up.start + 0.3, up.end - 0.2))
    overlays += [
        Overlay("badge-synthetic.png", intro.end, card.start),
        Overlay("badge-synthetic.png", card.end, ask.start),
    ]

    # Chips fade in as spoken and fade out when the upload segment begins.
    overlays += [Overlay(c.file, c.start, up.start, fade_in=True, fade_out=True) for c in chips]

    # Integrate: the results screen dims when the segment's voice starts, and each callout fades in
    # as its example is spoken. They all fade out together when the segment ends.
    if callouts:
        overlays.append(
            Overlay("backdrop.png", voice_start(integ), integ.end, fade_in=True, fade_out=True)
        )
        overlays += [
            Overlay(c.file, c.start, integ.end, fade_in=True, fade_out=True) for c in callouts
        ]

    # Intro: the logo fades in and out alone, then the title and subtitle fade in.
    overlays += [
        Overlay(
            "intro-logo.png",
            intro.start,
            intro.start + INTRO_LOGO_SECS,
            fade_in=True,
            fade_out=True,
            fade_in_secs=INTRO_LOGO_FADE_IN,
            fade_out_secs=INTRO_LOGO_FADE_OUT,
        ),
        Overlay(
            "intro-title.png",
            intro.start + INTRO_TITLE_AT,
            intro.end,
            fade_in=True,
            fade_in_secs=FADE_IN_SECS,
        ),
        Overlay(
            "intro-subtitle.png",
            intro.start + INTRO_TITLE_AT + INTRO_STAGGER,
            intro.end,
            fade_in=True,
            fade_in_secs=FADE_IN_SECS,
        ),
    ]

    # End card: the logo fades in as the voice finishes the question.
    overlays.append(
        Overlay(
            "endcard-logo.png",
            ask.end - END_LOGO_BEFORE_END,
            ask.end,
            fade_in=True,
            fade_in_secs=FADE_IN_SECS,
        )
    )

    # The intro card shows the same words the voice opens with, so captions start after it.
    # The end card already shows the question, so skip its caption (the SRT keeps it).
    overlays += [
        Overlay(c.file, max(c.start, intro.end), c.end)
        for c in cues
        if c.start < ask.start and c.end > intro.end
    ]

    return overlays


def overlay_graph(overlays: list[Overlay], first_idx: int) -> tuple[list[str], str]:
    """Filter lines that fade each overlay and composite it on `base`, and the final label."""
    lines, current = [], "base"
    for i, overlay in enumerate(overlays):
        src = f"{first_idx + i}:v"
        fade_lines = overlay.fade_lines(src, f"f{i}")
        lines.extend(fade_lines)
        src = f"[f{i}]" if fade_lines else f"[{src}]"
        lines.append(
            f"[{current}]{src}overlay=0:0:enable='between(t,{overlay.start:.3f},{overlay.end:.3f})'[o{i}]"
        )
        current = f"o{i}"

    return lines, current


def audio_graph(audio_files: list[tuple[float, Path]], first_idx: int, total: float) -> list[str]:
    """Filter lines that delay each segment's voice to its start time and mix them into [aout]."""
    lines = []
    for i, (start, _) in enumerate(audio_files):
        delay_ms = int(start * 1000)
        lines.append(f"[{first_idx + i}:a]adelay={delay_ms}|{delay_ms}[s{i}]")

    lines.append(
        "".join(f"[s{i}]" for i in range(len(audio_files)))
        + f"amix=inputs={len(audio_files)}:normalize=0,apad,atrim=duration={total}[aout]"
    )
    return lines


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument(
        "--mark-offset",
        type=float,
        default=0.5,
        help="seconds the video starts before the spec's clock (default 0.5)",
    )
    args = ap.parse_args()

    narration = load_narration()
    total = narration.total
    clips = find_clips(args.mark_offset)

    cues = build_cues(narration, args.no_audio)
    chips = build_chips(narration, args.no_audio)
    callouts = build_callouts(narration, args.no_audio)
    render_overlays(narration, cues, chips)

    video_inputs, still_inputs, graph = build_video_graph(clips, narration)
    up = narration.segment("upload")
    action_speed = (clips.demo.markers["results"] - clips.demo.markers["ready"]) / up.duration
    print(f"Upload action plays at {action_speed:.2f}x")
    overlays = build_overlays(narration, cues, chips, callouts, action_speed)

    # Inputs, in index order: video clips, stills, overlays, then voice.
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for p in video_inputs:
        cmd += ["-i", p]

    for still in still_inputs:
        cmd += [
            "-framerate",
            str(FPS),
            "-loop",
            "1",
            "-t",
            f"{still.duration:.3f}",
            "-i",
            str(OVERLAYS_DIR / still.name),
        ]

    first_overlay_idx = len(video_inputs) + len(still_inputs)
    for overlay in overlays:
        cmd += [
            "-framerate",
            str(FPS),
            "-loop",
            "1",
            "-t",
            str(total),
            "-i",
            str(OVERLAYS_DIR / overlay.file),
        ]

    overlay_lines, final_label = overlay_graph(overlays, first_overlay_idx)
    graph += overlay_lines

    audio_files = (
        []
        if args.no_audio
        else [(voice_start(b), OUTPUT_DIR / "audio" / f"{b.id}.wav") for b in narration.segments]
    )
    audio_files = [(s, p) for s, p in audio_files if p.exists()]
    for _, p in audio_files:
        cmd += ["-i", str(p)]

    audio_map = []
    if audio_files:
        graph += audio_graph(audio_files, first_overlay_idx + len(overlays), total)
        audio_map = ["-map", "[aout]", "-c:a", "aac", "-b:a", "160k"]

    out_file = OUTPUT_DIR / "documentai-trailer.mp4"
    cmd += [
        "-filter_complex",
        ";".join(graph),
        "-map",
        f"[{final_label}]",
        *audio_map,
        "-c:v",
        "libx264",
        "-crf",
        "20",
        "-preset",
        "medium",
        "-movflags",
        "+faststart",
        "-t",
        str(total),
        str(out_file),
    ]
    subprocess.run(cmd, check=True)
    print(
        f"Wrote {out_file} ({clip_duration(str(out_file)):.1f}s) and documentai-trailer.srt"
        f"{'' if audio_files else ' (no audio)'}"
    )


if __name__ == "__main__":
    main()
