# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = [
#   "kokoro-onnx==0.6.1",
# ]
# ///
"""Render the narration segments to WAV files with Kokoro-ONNX (local, offline).

Run with:  uv run docs/documentai-api/media/trailer/tts_kokoro.py [--voice af_heart] [--speed 1.0]
           uv run docs/documentai-api/media/trailer/tts_kokoro.py --emphasis-demo   # A/B/C emphasis samples

The model and voices files are downloaded once into out/models/ and checked
against the sha256 values in models.lock.json before use. Nothing is sent
anywhere except that one download from the pinned GitHub release.

Writes out/audio/<segment-id>.wav and out/audio/durations.json. timeline.py then
fits the segments to 60s and fails if the speech is too long.

Emphasis: wrap a word in asterisks in narration.json, like "What would *your*
agency". How it is spoken depends on the top-level "emphasis" setting:
  none      markers are removed; no change to the voice (default)
  punct     short pauses around the word (commas)
  segments  the word is spoken on its own, slower, between the surrounding text
  phonemes  the word gets a primary stress mark inside one continuous read
Captions and the end card show the word in bold either way.
"""

import argparse
import hashlib
import json
import re
import sys
import urllib.request
import wave
from pathlib import Path

import numpy as np
from kokoro_onnx import Kokoro

TRAILER_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = TRAILER_DIR / "out"
MODELS_DIR = OUTPUT_DIR / "models"
AUDIO_DIR = OUTPUT_DIR / "audio"
EMPH = re.compile(r"\*([^*]+)\*")
MODES = ("none", "punct", "segments", "phonemes")


def plain(text: str) -> str:
    return EMPH.sub(r"\1", text)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_models() -> None:
    lock = json.loads((TRAILER_DIR / "models.lock.json").read_text())
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for entry in lock["files"]:
        dest = MODELS_DIR / entry["name"]
        if not dest.exists():
            print(f"Downloading {entry['name']} ({entry['bytes'] / 1e6:.0f} MB)...")
            tmp = dest.with_suffix(dest.suffix + ".part")
            urllib.request.urlretrieve(entry["url"], tmp)
            tmp.rename(dest)
        actual = sha256(dest)
        if actual != entry["sha256"]:
            dest.unlink()
            sys.exit(f"sha256 mismatch for {entry['name']}: got {actual}, expected {entry['sha256']}. Deleted it.")
        print(f"ok  {entry['name']}  sha256 verified")


def write_wav(path: Path, samples: np.ndarray, rate: int) -> float:
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return len(pcm) / rate


def synth(kokoro: Kokoro, text: str, voice: str, speed: float, mode: str):
    """Speak `text`, applying `mode` to any *emphasised* words. Returns (samples, rate)."""
    create = lambda t, s=speed, **kw: kokoro.create(t, voice=voice, speed=s, lang="en-us", **kw)

    if "*" not in text or mode == "none":
        return create(plain(text))

    if mode == "punct":
        return create(EMPH.sub(lambda m: f", {m.group(1)},", text).replace(",,", ",").replace(", ,", ","))

    if mode == "segments":
        pieces, pos = [], 0
        for m in EMPH.finditer(text):
            if text[pos:m.start()].strip():
                pieces.append((text[pos:m.start()].strip(), False))
            pieces.append((m.group(1), True))
            pos = m.end()
        if text[pos:].strip():
            pieces.append((text[pos:].strip(), False))
        chunks, rate = [], None
        for i, (piece, emphasised) in enumerate(pieces):
            last = i == len(pieces) - 1
            # A trailing comma keeps a mid-sentence piece from sounding like a sentence end.
            spoken = piece if last else piece + ","
            samples, rate = create(spoken, speed * (0.82 if emphasised else 1.0))
            if emphasised:
                chunks.append(np.zeros(int(rate * 0.06), dtype=samples.dtype))
            chunks.append(samples)
        return np.concatenate(chunks), rate

    if mode == "phonemes":
        # Phonemize the text around each marked word separately (aligning espeak's
        # word tokens with ours is unreliable), then speak everything in one call so
        # the intonation stays continuous. The marked word gets a primary stress mark.
        phonemize = lambda t: kokoro.tokenizer.phonemize(t)
        parts, pos = [], 0
        for m in EMPH.finditer(text):
            if text[pos:m.start()].strip():
                parts.append(phonemize(text[pos:m.start()].strip()))
            word = phonemize(m.group(1))
            parts.append(word if "ˈ" in word else "ˈ" + word)
            pos = m.end()
        if text[pos:].strip():
            parts.append(phonemize(text[pos:].strip()))
        return create(" ".join(parts), is_phonemes=True)

    raise ValueError(f"unknown emphasis mode {mode!r}; use one of {MODES}")


def main() -> None:
    narration = json.loads((TRAILER_DIR / "narration.json").read_text())
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default=narration.get("voice", "af_heart"))
    ap.add_argument("--speed", type=float, default=narration.get("speed", 1.0))
    ap.add_argument("--emphasis", choices=MODES, default=narration.get("emphasis", "none"))
    ap.add_argument("--emphasis-demo", action="store_true",
                    help="render the closing line in every emphasis mode to out/audio/emphasis/")
    args = ap.parse_args()

    ensure_models()
    kokoro = Kokoro(str(MODELS_DIR / "kokoro-v1.0.onnx"), str(MODELS_DIR / "voices-v1.0.bin"))

    if args.emphasis_demo:
        demo = AUDIO_DIR / "emphasis"
        demo.mkdir(parents=True, exist_ok=True)
        ask = next(b for b in narration["segments"] if b["id"] == "ask")["text"]
        if "*" not in ask:
            sys.exit('Mark a word in the "ask" segment first, e.g. "What would *your* agency ...".')
        for mode in MODES:
            samples, rate = synth(kokoro, ask, args.voice, args.speed, mode)
            dur = write_wav(demo / f"ask-{mode}.wav", samples, rate)
            print(f"ask-{mode}.wav  {dur:.1f}s")
        print(f"Samples are in {demo}")
        return

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    durations = {}
    for segment in narration["segments"]:
        samples, rate = synth(kokoro, segment["text"], args.voice, args.speed, args.emphasis)
        dur = write_wav(AUDIO_DIR / f"{segment['id']}.wav", samples, rate)
        durations[segment["id"]] = round(dur, 2)
        print(f"{segment['id']:<10} {dur:5.1f}s")

    (AUDIO_DIR / "durations.json").write_text(json.dumps(durations, indent=2))


if __name__ == "__main__":
    main()
