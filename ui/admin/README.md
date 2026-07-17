# DocumentAI Admin UI

Admin console for managing API keys, tenants, users, extraction rules, and document processing.

## Prerequisites

- Node.js 20.19+ (required by Vitest 4 / Rolldown; Node 18 fails at test startup)
- npm

## Setup

```bash
nvm use                           # selects the version in .nvmrc (Node 22)
npm install
cp config.example.json config.json
npx playwright install chromium  # for e2e tests
```

Serves at `localhost:3000`. Update `config.json` with your API endpoint and Cognito values if you haven't deployed yet. In production, `config.json` is generated automatically by the infrastructure deploy.

## Commands

| Command | Description |
|---------|-------------|
| `npm run dev` | Dev server at localhost:3000 |
| `npm run build` | Production bundle -> `dist/bundle.js` |
| `npm test` | Unit tests (Vitest) |
| `npm run test:watch` | Unit tests in watch mode |
| `npm run test:e2e` | e2e tests (Playwright) |
| `npm run lint` | ESLint |
| `npm run format` | Prettier |

Deploy from the repo root: `make deploy-admin-ui`

## Recording demo videos

Requires `ffmpeg` (`brew install ffmpeg`) and Chromium (`make playwright-install`).

```bash
make record-admin-ui       # admin console walkthrough -> admin-walkthrough.gif
make record-rules-ui       # extraction rules walkthrough -> admin-extraction-rules-walkthrough.gif
make record-ui             # all videos (admin + rules + demo)
```

Specs live in `e2e-video/`. See [e2e-video/README.md](e2e-video/README.md) for what to edit.

## Auth model

- Admin users authenticate via Cognito (email + password + optional TOTP MFA)
- Roles: `super-admin` (full access), `tenant-admin` (scoped to tenant)
- New users land on a pending screen until approved by a super-admin
- 15-minute inactivity timeout with GlobalSignOut
- Global 401 interceptor clears session and redirects to login

## Project structure

```
src/
├── main.js                         - entry point, router, view lifecycle
├── views/
│   ├── login/                      - sign-in, sign-up, MFA, forgot-password
│   ├── keys/                       - API key management
│   ├── tenants/                    - tenant CRUD
│   ├── users/                      - user approval, role assignment
│   ├── extraction-rules/           - blueprint field rule editor
│   ├── documents/                  - document viewer with detail panel
│   ├── document-categories/        - category management
│   ├── test-documents/             - BDA extraction test runner
│   ├── audit-log/                  - audit event viewer
│   ├── sidebar/                    - dashboard shell + nav
│   └── pending/                    - pending approval screen
├── services/                       - API client wrappers
├── panes/                          - extraction-rules sub-components
├── state/                          - shared store (blueprint-store)
└── utils/                          - session, toast, dom, modal, tenant-context
styles/
└── style.css                       - global styles, design tokens, responsive
tests/
├── factories.js                    - test data factories (buildTenant, buildUser, etc.)
├── helpers.js                      - DOM interaction helpers
├── views/                          - view unit tests
├── panes/                          - pane unit tests
├── services/                       - service wrapper tests
├── state/                          - store tests
└── utils/                          - utility tests
e2e/
├── login.spec.js                   - auth flow
├── navigation.spec.js              - routing + view mount/unmount
└── mfa.spec.js                     - MFA setup + verify
e2e-video/
├── admin-walkthrough.spec.js       - scripted admin console recording
└── admin-extraction-rules-walkthrough.spec.js - scripted extraction rules recording
```
