# Admin console demo videos

Re-generatable UI walkthroughs of the admin console. Every network dependency
(`config.json`, Cognito, all API endpoints) is mocked so specs run **offline,
deterministically, with no credentials or deployed infra**.

## Specs

| Spec | Flow | Output |
|------|------|--------|
| `admin-walkthrough.spec.js` | start logged in -> Console Access (Audit Log, Users) -> API Management (API Keys, Manage Blueprints, Doc Categories, Extraction Rules) -> Documents -> QA Tools -> Reporting (Metrics, Usage) | `admin-walkthrough.gif` |
| `admin-extraction-rules-walkthrough.spec.js` | start logged in -> Extraction Rules -> select tenant -> browse blueprints -> toggle fields -> save | `admin-extraction-rules-walkthrough.gif` |
| `document-viewer-walkthrough.spec.js` | start logged in -> Documents -> document viewer with bbox and field highlighting | `document-viewer-walkthrough.gif` |
| `extraction-test-runner-walkthrough.spec.js` | start logged in -> QA Tools -> select tenant -> drop file -> run -> result renders | `extraction-test-runner-walkthrough.gif` |

## Regenerate

From the repo root:

```bash
make record-ui   # records every e2e-video/*.spec.js in both UIs
```

First run: `make playwright-install` (installs Chromium) and ensure `ffmpeg` is available (`brew install ffmpeg`).

The spec filename stem becomes the GIF name — `foo-walkthrough.spec.js` produces `foo-walkthrough.gif` in `docs/documentai-api/media/`. To add a new recording, drop a `*.spec.js` in this directory; no Makefile changes needed.

## What to edit

- **Synthetic data** - arrays at the top of each spec (`TENANTS`, `KEYS`, `USERS`, `DOCUMENTS`, `FIELDS`)
- **Shared W-2 fixture** - `ui/shared/e2e/fixtures/recording/w2-document.js`
- **Pacing** - `launchOptions.slowMo` in `playwright.video.config.js` and `waitForTimeout` calls in the spec
- **Flow** - add or reorder navigation steps in the test body
