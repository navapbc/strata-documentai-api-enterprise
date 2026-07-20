# DocumentAI Demo UI

Minimal demo app for uploading documents and viewing extraction results with bounding box overlay. Scoped to the authenticated user's tenant - no admin features.

## Prerequisites

- Node.js 20.19+
- npm

## Setup

```bash
nvm use
npm install
cp config.example.json config.json
npx playwright install chromium  # for e2e tests
```

Serves at `localhost:3001`. Update `config.json` with your API endpoint and Cognito values if you haven't deployed yet.

## Commands

| Command | Description |
|---------|-------------|
| `npm run dev` | Dev server at localhost:3001 |
| `npm run build` | Production bundle -> `dist/` |
| `npm test` | Unit tests (Vitest) |
| `npm run test:watch` | Unit tests in watch mode |
| `npm run test:e2e` | e2e tests (Playwright) |
| `npm run lint` | ESLint |
| `npm run format` | Prettier |

Deploy from the repo root: `make deploy-demo-ui`

## Recording demo videos

Requires `ffmpeg` (`brew install ffmpeg`) and Chromium (`make playwright-install`).

```bash
make record-demo-ui    # demo UI walkthrough -> demo-walkthrough.gif
make record-ui         # all videos (admin + rules + demo)
```

The spec lives in `e2e-video/demo-walkthrough.spec.js`. See [e2e-video/README.md](e2e-video/README.md) for what to edit.

## Project structure

```
src/
├── main.js              - entry point, auth init, view routing
├── views/
│   ├── login/           - sign-in, MFA
│   └── upload/          - document upload, polling, results + bbox overlay
└── services/
    └── documents.js     - API client (upload, poll, history)
styles/
└── style.css
tests/                   - unit tests (Vitest)
e2e/                     - e2e tests (Playwright, real backend)
e2e-video/
└── demo-walkthrough.spec.js  - scripted demo recording (mocked, offline)
```
