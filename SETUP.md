# Setup and deploy

## Requirements

- AWS CLI with a profile that has permission to create the required infrastructure
- Terraform 1.10 or newer
- Docker
- Node.js 20 or newer (22 recommended)
- Python 3.11 or newer with [uv](https://github.com/astral-sh/uv)
- ffmpeg - only needed for regenerating demo GIFs (`brew install ffmpeg`)

## First-time setup

1. Enable the local git hooks. Runs a [gitleaks](https://github.com/gitleaks/gitleaks) secret scan on staged changes before each commit:

```bash
make install-hooks
```

2. Set your AWS profile:

```bash
export AWS_PROFILE=your-profile
```

3. Bootstrap the Terraform state bucket (once per environment):

```bash
cd infra
make infra-bootstrap ENVIRONMENT=dev
make infra-init ENVIRONMENT=dev
```

4. Deploy:

```bash
cd ..
make deploy
```

This builds the API container, applies Terraform, builds the admin UI, syncs it to S3, and invalidates CloudFront. The admin UI `config.json` is generated automatically from Terraform outputs.

## Deploy

From the repo root:

```bash
make deploy
```

Deploy pieces separately:

```bash
make deploy-infra   # Docker image + Terraform only
make deploy-ui      # Admin and demo UIs only
```

With a specific environment or profile:

```bash
make deploy ENVIRONMENT=dev AWS_PROFILE=my-profile
```

Region is configured in `infra/environments/<env>/terraform.tfvars`. The state bucket is always created in `us-east-1`.

Only the `dev` environment exists today. To add another, copy `infra/environments/dev/` and update its `terraform.tfvars`, then run `make infra-bootstrap ENVIRONMENT=<name>`.

## Local development

### API

```bash
cd documentai-api
cp local.env.example .env
make init
make start
```

Runs at `localhost:8000`. The default `.env` sets `API_AUTH_INSECURE_SHARED_KEY=local-dev-key` - use `API-Key: local-dev-key` in requests. No DynamoDB or Cognito needed.

See [documentai-api/README.md](documentai-api/README.md) for the full command reference.

### Admin UI

```bash
cd ui/admin
npm install
cp config.example.json config.json
npm run dev
```

Runs at `localhost:3000`. If you haven't deployed yet, update `config.json` with your API endpoint and Cognito values.

### Demo UI

```bash
cd ui/demo
npm install
cp config.example.json config.json
npm run dev
```

Runs at `localhost:3001`.

## Teardown

```bash
cd infra
make infra-destroy ENVIRONMENT=dev
```

S3 buckets with objects and ECR repositories with images may block destroy - empty them first. The Terraform state bucket is not destroyed by design.
