# DocumentAI Trailer

Rebuilds the one-minute screen recording with voiceover and captions from
scripted Playwright runs, so it can be regenerated after UI changes. Everything
on screen is synthetic and mocked: no credentials, no deployed infrastructure.

```bash
make trailer                    # record, narrate, assemble (about 90s)
make trailer args=--no-audio    # silent build, no Kokoro
```

`make trailer` runs `docs/documentai-api/media/trailer/build.sh` after making sure
Chromium is installed. You can also run that script directly.

Output goes to `docs/documentai-api/media/trailer/out/` (gitignored): `documentai-trailer.mp4` with
burned-in captions, and `documentai-trailer.srt` for a separate caption track.

## Timeline

The video has a fixed length, `TOTAL` in `timeline.py` (60s). The scenes run in this
order; the start and end of each come from the measured speech and are printed by
`timeline.py` (and saved in `out/timeline.json`), so they are not repeated here.

| Scene | Shows | Source |
|-------|-------|--------|
| Intro | The Nava logo fades in and out, then the "DocumentAI" title and tagline fade in as the voice starts | `narration.json` `intro` |
| `overview` | Overview narration over the ready upload screen; chips appear as each requirement is named | demo spec, held frame |
| `upload` | Upload a synthetic pay stub; processing (labelled "Edited" if it is sped up) | demo spec, real action |
| `inspect` | Extracted fields beside the source document; the flagged low-confidence field last | demo spec, results |
| `integrate` | The results screen dims and three illustrative panels fade in as the voice names each example: the existing design system's components, a blurry upload with a "too blurry" alert, then a mock caseworker portal prefilled with the extracted values | `narration.json` `callouts` |
| Admin card | "Administrator view" title card | `narration.json` `interstitial` |
| `configure` | Required fields defined for the Pay Stub document type | `ui/admin/e2e-trailer/trailer-admin.spec.js` "rules" |
| `monitor` | Metrics dashboard: volume, outcomes, processing time | same spec, "metrics" |
| `ask` | The closing question and repository link (end card); the Nava logo fades in at the bottom | `narration.json` |

The timeline comes from measured speech at the voice speed set in `narration.json`. `make trailer`
records the clips, renders the voice, builds the timeline (`timeline.py`, written
to `out/timeline.json`) and assembles, so the whole chain re-runs on every build.
`timeline.py` fails if the speech no longer fits `TOTAL` (shorten the text or raise
`speed`). Segment ends round up to whole seconds, so a small text change can cost or
save a full second. Voice speed is not linear: small `speed` changes can move the
total by several seconds, so re-run `timeline.py` after changing it.

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
- `"voiceStart"` on the overview segment starts its voice at an absolute time,
  over the intro card, instead of after the segment opens. The intro is timed to it:
  the Nava logo fades in and out first, then the title fades in as the voice starts
  (the `INTRO_*` constants in `assemble.py`). Captions skip the intro card. The end
  card fades the logo in at the bottom as the voice finishes (`END_LOGO_BEFORE_END`).
  The logo is `../logos/Nava-Logo.svg`, a copy of the Nava Strata logo without the "strata"
  wordmark, inlined and filled white by `render_overlays.mjs`.

## What is committed

- `narration.json`, `models.lock.json`, `tts_kokoro.py`, `timeline.py`, `narration.py`,
  `assemble.py` (with `captions.py`, `timing.py`, `clips.py`, `overlay.py`), `render_overlays.mjs`, `overlays.html`, `overlays.js`, `overlays.css`, `build.sh`, `icons/` (Heroicons, MIT; see
  `THIRD_PARTY_NOTICES.md` at the repo root), this README, and the trimmed logo
  `../logos/Nava-Logo.svg`
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

## Where things live

| File | Holds |
|------|-------|
| `narration.json` | The hand-written content: voiceover text, intro and title cards, chips, callouts, end card |
| `narration.py` | Loads it into `Narration`, `Segment` and `Card`; `load()` also merges in `out/timeline.json` |
| `tts_kokoro.py` | Renders each segment's voice to WAV and records how long each is |
| `timeline.py` | Lays the segments out within `TOTAL` from the measured speech |
| `timing.py` | Voice start times and the estimated times of spoken words, chips and callouts |
| `captions.py` | Splits the narration into caption cues and writes the SRT |
| `clips.py` | The recordings and their markers (`Recording`, `Cut`), and `ClipEdit`, which builds the ffmpeg chain that fits a clip to its window |
| `overlay.py` | `Overlay`, a PNG shown for part of the timeline, with its alpha fades |
| `assemble.py` | Puts it together: the filter graph, overlay schedule and audio mix, then runs ffmpeg |
| `render_overlays.mjs`, `overlays.*` | Draws the text overlays as transparent PNGs in Chromium |

### Format and lint

- The Python follows the API's ruff settings (`documentai-api/pyproject.toml`) and is checked by
  `make format` and `make lint`. The scripts carry `# ruff: noqa: INP001` because they are
  scripts, not a package.
- `render_overlays.mjs`, `overlays.js` and `overlays.css` are checked by `ui/demo`'s
  `npm run format:check`, and the `e2e-trailer/` specs by both UIs'. `overlays.html` is left out:
  prettier would change the whitespace inside its inline templates.

## How the timing works

Playwright records each flow at its natural pace. `assemble.py` retimes each clip
to its segment window: sped up when longer, last frame held when shorter. The
specs write marks (`video-output/trailer-demo-marks.json`,
`trailer-admin-marks.json`) so the demo clip is split where results appear and
the admin clips start after sign-in rather than on the login screen. If a retimed
clip looks off by a fraction of a second, adjust `--mark-offset`.

## Things to know

- The `integrate` panels are drawn in Chromium like the other overlays (`callout-*` templates in
  `overlays.html`). The blurry page is a real fixture,
  `documentai-api/tests/helpers/fixtures/test-documents/blur/synthetic-disk-defocus.jpeg`, so
  keep that file or point `render_overlays.mjs` at another. The portal values mirror
  `ui/shared/e2e/fixtures/recording/pay-stub-document.js`; update them if that fixture changes.
- The text overlays (captions, label, end card) are drawn in Chromium and
  composited as PNGs, because the local ffmpeg build has no `drawtext` or
  `subtitles` filter.
- The metrics chart dates read 7/10-7/16: they come from the shared admin
  fixture. The timing chart needs `dailyStats[].timingStats`, which that fixture
  stores flat, so `trailer-admin.spec.js` reshapes it locally.
- The repository link on the end card is read from `narration.json`. Make sure
  that repository is reachable by whoever watches the video.
