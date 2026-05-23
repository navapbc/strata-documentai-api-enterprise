# DocAI Admin UI

Admin interface for managing DocumentAI API keys and extraction rules.

## Setup

```bash
npm install
```

## Development

```bash
npm run dev
```

Opens at http://localhost:3000. Hot-reloads on file changes.

## Build

```bash
npm run build
```

Outputs minified bundle to `dist/bundle.js`.

## Demo Mode

Navigate to `http://localhost:3000?demo=true` or click "Demo Mode" on the login screen.

## Project Structure

```
js/
├── utils/          — shared helpers (session, toast, formatting)
├── services/       — API layer (http client, keys, schemas, rules)
├── demo/           — mock data for demo mode
├── views/          — UI components (login, keys, blueprints, search)
└── main.js         — entry point (routing, init)
styles/
└── style.css       — all styles
dist/
└── bundle.js       — bundled output (generated)
```

## Deployment

```bash
npm run build
aws s3 sync . s3://your-bucket --exclude "node_modules/*" --exclude "js/*" --exclude ".git/*" --exclude "package*"
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Connection test |
| GET | `/v1/admin/api-keys` | List all keys |
| POST | `/v1/admin/api-keys` | Create key |
| DELETE | `/v1/admin/api-keys/{tenant}/{user}` | Revoke key |
| POST | `/v1/admin/api-keys/request` | Self-service key request |
| GET | `/v1/dictionary/schemas` | List blueprints |
| GET | `/v1/dictionary/schemas/{type}` | Get schema |
| GET | `/v1/config/extraction-rules` | Get rules |
| PUT | `/v1/config/extraction-rules` | Save rules |
| DELETE | `/v1/config/extraction-rules` | Delete rules |
