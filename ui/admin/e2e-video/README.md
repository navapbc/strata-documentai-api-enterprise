# Admin console demo videos

Re-generatable UI walkthroughs of the admin console. Every network dependency
(`config.json`, Cognito, all API endpoints) is mocked so specs run **offline,
deterministically, with no credentials or deployed infra**.

## Specs

| Spec | Flow | Output |
|------|------|--------|
| `admin-walkthrough.spec.js` | login -> MFA -> Tenants -> Users -> API Keys -> Documents (W-2 detail + field highlights) | `admin-walkthrough.gif` |
| `admin-extraction-rules-walkthrough.spec.js` | login -> MFA -> Extraction Rules -> select tenant -> browse blueprints -> toggle fields -> save | `admin-extraction-rules-walkthrough.gif` |

## Regenerate

From the repo root:

```bash
make record-admin-ui       # admin walkthrough
make record-rules-ui       # extraction rules walkthrough
make record-ui             # all videos (admin + rules + demo)
```

First run: `make playwright-install` (installs Chromium) and ensure `ffmpeg` is available (`brew install ffmpeg`).

## What to edit

- **Synthetic data** - arrays at the top of each spec (`TENANTS`, `KEYS`, `USERS`, `DOCUMENTS`, `FIELDS`)
- **Shared W-2 fixture** - `ui/shared/e2e/fixtures/recording/w2-document.js`
- **Pacing** - `launchOptions.slowMo` in `playwright.video.config.js` and `waitForTimeout` calls in the spec
- **Flow** - add or reorder navigation steps in the test body
