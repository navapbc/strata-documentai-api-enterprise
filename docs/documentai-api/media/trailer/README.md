# Trailer

Rebuilds the one-minute screen recording with voiceover and captions from
scripted Playwright runs, so it can be regenerated after UI changes. Everything
on screen is synthetic and mocked: no credentials, no deployed infrastructure.

```bash
make trailer                    # record, narrate, assemble (about 90s)
make trailer args=--no-audio    # silent build, no Kokoro
```

`make trailer` runs `docs/documentai-api/media/trailer/build.sh` after making sure
Chromium is installed. You can also run that script directly.

Output goes to `docs/documentai-api/media/trailer/out/` (gitignored): `trailer.mp4` with
burned-in captions, and `trailer.srt` for a separate caption track.

## Timeline

| Time | Shows | Source |
|------|-------|--------|
| 0-1.5s | "DocumentAI" title card | `narration.json` `intro` |
| 1.5-17.7s | Overview narration over the ready upload screen | demo spec, held frame |
| 17.7-23.2s | Upload a synthetic pay stub; processing (about 1.5x, labelled "Edited") | demo spec, real action |
| 23.2-34.5s | Extracted fields beside the source document; the flagged low-confidence field last | demo spec, results |
| 34.5-36s | "Administrator view" title card | `narration.json` `interstitial` |
| 36-46.6s | Required fields defined for the Pay Stub document type | `ui/admin/e2e-trailer/trailer-admin.spec.js` "rules" |
| 46.6-54.5s | Metrics dashboard: volume, outcomes, processing time | same spec, "metrics" |
| 54.5-60s | The closing question and repository link (end card) | `narration.json` |

The timeline comes from measured speech at voice speed 1.25. `make trailer`
records the clips, renders the voice, builds the timeline (`timeline.py`, written
to `out/timeline.json`) and assembles, so the whole chain re-runs on every build.
`timeline.py` fails if the speech no longer fits 60s (shorten the text or raise
`speed`).

`narration.json` holds only hand-written content: voiceover text, captions, the
end card, chips, and the title card text and lengths. During the overview, chips
appear as each listed word is spoken; their timing is estimated from the word's
position in the text.

## When something changes

| You changed | Do |
|-------------|----|
| Narration text, chips, end card | `make trailer` (the voice and timeline are redone). `args=--no-audio` skips the voice and reuses `out/timeline.json` from the last full build. |
| Demo or admin UI (selectors, layout) | Run the specs: `cd ui/demo && npx playwright test --config=playwright.trailer.config.js` (same for admin). A selector failure means the spec needs updating; then `make trailer`. |
| API response shape | Update the mocked data: `ui/shared/e2e/fixtures/recording/pay-stub-document.js` (demo) and `trailer-admin.spec.js` (metrics). |
| Pill, captions, chips, card look | `overlays.css` (markup in `overlays.html`, template filling in `overlays.js`) |

The specs are not part of CI, so UI breakage shows up the next time someone builds.

The recording reuses a dev server already running on port 3000 (admin) or 3001
(demo). If a build hangs on the first screen, check that those ports are served by
the UIs and not by something else (the failed test's `error-context.md` shows the
page it saw).

## Emphasis and early voice

- Wrap a word in asterisks in `narration.json`, like `What would *your* agency`.
  Captions show it bold; the end card keeps it plain white. How the voice stresses it is the top-level `"emphasis"` setting: `none`,
  `punct`, `segments`, or `phonemes`. To compare them by ear:

  ```bash
  uv run docs/documentai-api/media/trailer/tts_kokoro.py --emphasis-demo   # writes out/audio/emphasis/ask-<mode>.wav
  ```

  Set the winner in `narration.json`, then run `make trailer`.
- `"voiceStart"` on the overview segment starts its voice at an absolute time (0.15s),
  over the title card, instead of after the segment opens. Captions skip the title card.

## What is committed

- `narration.json`, `models.lock.json`, `tts_kokoro.py`, `timeline.py`, `narration.py`,
  `assemble.py`, `render_overlays.mjs`, `overlays.html`, `overlays.js`, `overlays.css`, `build.sh`, `icons/` (Heroicons, MIT; see
  `THIRD_PARTY_NOTICES.md` at the repo root), this README
- The Playwright specs and configs in `ui/{demo,admin}/e2e-trailer/` and
  `playwright.trailer.config.js`, plus the pay stub fixture in
  `ui/shared/e2e/fixtures/recording/pay-stub-document.js`

Not committed: model weights, audio, overlays, the final video, and Playwright's
`video-output/` (already ignored in each UI).

The specs are in `e2e-trailer/`, not `e2e-video/`, on purpose: `make record-ui`
only globs `e2e-video/`, so recording the trailer never writes GIFs into the
docs media folder.

## Voice

`tts_kokoro.py` uses [Kokoro-ONNX](https://github.com/thewh1teagle/kokoro-onnx)
locally; no text leaves your machine. On first run it downloads two files from a
pinned GitHub release into `out/models/` (about 354 MB) and refuses to use them
unless their sha256 matches `models.lock.json`. ONNX and the voices archive are
data formats, not pickled Python. Check the voice's license on the model card
before distributing the video.

Change the voice with `uv run docs/documentai-api/media/trailer/tts_kokoro.py --voice am_michael`.
To use a recorded human voice instead, drop one WAV per segment in `out/audio/`
named after the segment id (`upload.wav`, `inspect.wav`, ...) and run
`assemble.py` directly.

## How the timing works

Playwright records each flow at its natural pace. `assemble.py` retimes each clip
to its segment window: sped up when longer, last frame held when shorter. The
specs write marks (`video-output/trailer-demo-marks.json`,
`trailer-admin-marks.json`) so the demo clip is split where results appear and
the admin clips start after sign-in rather than on the login screen. If a retimed
clip looks off by a fraction of a second, adjust `--mark-offset`.

## Things to know

- The text overlays (captions, label, end card) are drawn in Chromium and
  composited as PNGs, because the local ffmpeg build has no `drawtext` or
  `subtitles` filter.
- The metrics chart dates read 7/10-7/16: they come from the shared admin
  fixture. The timing chart needs `dailyStats[].timingStats`, which that fixture
  stores flat, so `trailer-admin.spec.js` reshapes it locally.
- The repository link on the end card is read from `narration.json`. Make sure
  that repository is reachable by whoever watches the proposal.
