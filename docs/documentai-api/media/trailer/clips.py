"""The recorded clips, and the ffmpeg filter chain that edits each one to its segment window."""

import glob
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Self

from narration import REPO_ROOT, TRAILER_DIR

W, H, FPS = 1280, 800, 25
CLIP_FADE_SECS = 0.3

# Where the trailer specs leave their recordings and marks, relative to the repo root.
DEMO_GLOB = "ui/demo/video-output/trailer-demo-*/video.webm"
RULES_GLOB = "ui/admin/video-output/trailer-admin-rules-*/video.webm"
METRICS_GLOB = "ui/admin/video-output/trailer-admin-metrics-*/video.webm"
DEMO_MARKS = "ui/demo/video-output/trailer-demo-marks.json"
ADMIN_MARKS = "ui/admin/video-output/trailer-admin-marks.json"


def clip_duration(path: str) -> float:
    """Return the duration in seconds of a video file by calling ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


@dataclass
class Recording:
    """A recorded video file, its length, and the moments in it the specs flagged (seconds into the file)."""

    path: str
    length: float
    markers: dict[str, float]

    @classmethod
    def latest(cls, pattern: str, markers: dict[str, float]) -> Self:
        """The most recently recorded clip matching a glob pattern.
        Directories are timestamped so the last entry alphabetically is the newest."""
        matches = sorted(glob.glob(str(REPO_ROOT / pattern)))
        if not matches:
            sys.exit(f"No clip matches {pattern}. Record first (see README).")
        return cls(matches[-1], clip_duration(matches[-1]), markers)


@dataclass
class Clips:
    """The recorded clips. Markers: demo `ready` (upload screen ready) and `results` (extracted
    results appear); admin `start` (the screen starts, after sign-in)."""

    demo: Recording
    rules: Recording
    metrics: Recording


@dataclass
class Cut:
    """A stretch [start, end] of one recording."""

    recording: Recording
    start: float
    end: float


def find_clips(mark_offset: float) -> Clips:
    """Locate the latest recordings and read the marks the specs wrote beside them."""
    demo_marks = json.loads((REPO_ROOT / DEMO_MARKS).read_text())
    admin_marks = json.loads((REPO_ROOT / ADMIN_MARKS).read_text())
    return Clips(
        demo=Recording.latest(
            DEMO_GLOB,
            {"ready": demo_marks["readyAtSec"] + mark_offset, "results": demo_marks["resultsAtSec"] + mark_offset},
        ),
        rules=Recording.latest(RULES_GLOB, {"start": admin_marks["rules"] + mark_offset}),
        metrics=Recording.latest(METRICS_GLOB, {"start": admin_marks["metrics"] + mark_offset}),
    )


def _card_color() -> str:
    """The title-card background, read from overlays.css so the clips fade into the same color."""
    match = re.search(r"--card-bg:\s*#([0-9a-fA-F]{6})", (TRAILER_DIR / "overlays.css").read_text())
    if not match:
        raise SystemExit("Could not find a '--card-bg: #rrggbb' line in overlays.css")
    return "0x" + match.group(1)


CLIP_FADE_COLOR = _card_color()  # clips fade through the card color instead of hard-cutting


class ClipEdit:
    """Builds an ffmpeg video filter chain for a single input clip."""

    def __init__(self, input_index: int, start: float, end: float) -> None:
        self._parts = [f"[{input_index}:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS"]
        self._clip_secs = end - start  # the clip as recorded
        self._fitted_secs: float | None = None  # its length once fitted (and held), if known

    @classmethod
    def still(cls, input_index: int, seconds: float) -> Self:
        """For a looped still-image input: just normalize to `seconds` duration."""
        edit = object.__new__(cls)
        edit._parts = [f"[{input_index}:v]null"]  # a first filter, so later parts can be comma-joined
        edit._clip_secs = seconds
        edit._fitted_secs = seconds
        return edit

    def fit_to_duration(self, seconds: float) -> Self:
        """Speed up or pad to exactly `seconds`."""
        if self._clip_secs > seconds:
            self._parts.append(f"setpts=PTS*{seconds / self._clip_secs:.5f}")
        elif self._clip_secs < seconds:
            self._parts.append(f"tpad=stop_mode=clone:stop_duration={seconds - self._clip_secs:.3f}")

        self._fitted_secs = seconds
        return self

    def hold_start(self, seconds: float) -> Self:
        """Prepend a freeze-frame of `seconds` before the clip action."""
        self._parts.append(f"tpad=start_mode=clone:start_duration={seconds:.3f}")
        if self._fitted_secs is not None:
            self._fitted_secs += seconds
        return self

    def normalize(self, seconds: float | None = None) -> Self:
        """Enforce fps/scale/pixel-format and hard-trim to the final duration (`seconds`, else the fitted length)."""
        final_secs = seconds or self._fitted_secs or self._clip_secs
        self._parts.append(
            f"fps={FPS},scale={W}:{H},format=yuv420p,trim=duration={final_secs:.3f},setpts=PTS-STARTPTS"
        )
        return self

    def fade_in(self, seconds: float = CLIP_FADE_SECS) -> Self:
        """Fade in from the card color over `seconds`."""
        self._parts.append(f"fade=t=in:st=0:d={seconds}:color={CLIP_FADE_COLOR}")
        return self

    def fade_out(self, seconds: float = CLIP_FADE_SECS) -> Self:
        """Fade out to the card color over the last `seconds`."""
        start = (self._fitted_secs or self._clip_secs) - seconds
        self._parts.append(f"fade=t=out:st={start:.3f}:d={seconds}:color={CLIP_FADE_COLOR}")
        return self

    def label(self, output_label: str) -> str:
        """The finished chain as one filter graph line, its output named `[output_label]`."""
        return ",".join(self._parts) + f"[{output_label}]"

    def __str__(self) -> str:
        return ",".join(self._parts)
