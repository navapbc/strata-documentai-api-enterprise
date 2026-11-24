# These are standalone scripts, not a package.
# ruff: noqa: INP001
"""A PNG overlay shown on top of the video for part of the timeline, with optional alpha fades."""

from dataclasses import dataclass

from clips import CLIP_FADE_SECS


@dataclass
class Overlay:
    file: str
    start: float
    end: float
    fade_in: bool = False
    fade_out: bool = False
    fade_in_secs: float = CLIP_FADE_SECS
    fade_out_secs: float = 0.25

    def fade_lines(self, input_label: str, output_label: str) -> list[str]:
        """Filter lines that fade this overlay's alpha, from `[input_label]` to `[output_label]`.

        Empty when the overlay has no fades, so the caller uses the input as is.
        """
        if not self.fade_in and not self.fade_out:
            return []

        chain = f"[{input_label}]format=rgba"
        if self.fade_in:
            chain += f",fade=t=in:st={self.start:.3f}:d={self.fade_in_secs}:alpha=1"

        if self.fade_out:
            chain += (
                f",fade=t=out:st={self.end - self.fade_out_secs:.3f}:d={self.fade_out_secs}:alpha=1"
            )

        return [chain + f"[{output_label}]"]
