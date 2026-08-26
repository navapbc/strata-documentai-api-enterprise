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

### API Setup Walkthrough

<!-- GitHub doesn't render locally hosted MP4s referenced from a README as
inline videos. Upload the video through GitHub's attachment system and use the
resulting github.com/user-attachments/assets/... URL.
-->
<video src="https://github.com/user-attachments/assets/6518f44b-e689-4d48-87bc-46e14b50c8a1" controls width="100%"></video>

### API Setup Steps

```bash
cd documentai-api
cp local.env.example .env
make env-from-aws   # Required for document upload; optional otherwise - see below
make init
make start
```

Runs at `localhost:8000`. The default `.env` sets `API_AUTH_INSECURE_SHARED_KEY=local-dev-key` - use `API-Key: local-dev-key` in requests. No DynamoDB or Cognito needed for auth or `/health`/`/v1/me`.

`POST /v1/documents` requires deployed AWS resources; the `documentai-*-local` placeholders in `local.env.example` do not exist in AWS. Execute `make env-from-aws` (with an AWS profile granting dev account access) to point `.env` at the real dev tables, buckets, and BDA project.

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
