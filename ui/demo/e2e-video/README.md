# Scripted demo video

A re-generatable UI walkthrough of the demo app — the browser analog of a
terminal (VHS) recording. It drives the real SPA through
**login → MFA → upload → extraction results with the bounding-box overlay**, but
mocks every network dependency (`config.json`, Cognito, the API) so it runs
**offline, deterministically, with no credentials or deployed infra**.

> This is separate from [`../e2e/upload.spec.js`](../e2e/upload.spec.js), which
> is the *real-backend* e2e (live API + Cognito + real BDA, needs credentials).
> Use that to validate the true integration; use this to produce a demo clip.

## Regenerate

Requires Node ≥ 20.19 (use Node 22). From `ui/demo`:

```bash
npm install                      # first time only
npx playwright install chromium  # first time only
npx playwright test --config=playwright.video.config.js
```

Output: `video-output/<test>/video.webm` (1280×800).

## Make a GIF

```bash
../shared/scripts/webm-to-gif.sh video-output/*/video.webm video-output/demo-walkthrough.gif
# optional: ../shared/scripts/webm-to-gif.sh <in.webm> <out.gif> <fps> <width>
```

## What to edit

- **The document / extracted fields** — the `FIELDS` array in `demo-walkthrough.spec.js` is
  the single source of truth: it draws the synthetic W-2 preview *and* derives
  the normalised bounding boxes, so overlay boxes always land on the values.
- **Pacing** — `launchOptions.slowMo` in `playwright.video.config.js` plus the
  `waitForTimeout` beats in the spec.
- **Mocked responses** — the `page.route(...)` handlers at the top of the test.
