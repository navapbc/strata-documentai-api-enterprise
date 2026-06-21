# Infrastructure

Terraform modules for the DocumentAI serverless platform.

## Prerequisites

- Terraform 1.10+
- AWS CLI configured
- Docker (for Lambda container builds)

## Quick Start

```bash
# First time: create state bucket
make infra-bootstrap ENVIRONMENT=dev

# Initialize Terraform
make infra-init ENVIRONMENT=dev

# Full deploy (build Docker image + apply)
make infra-deploy ENVIRONMENT=dev
```

## Commands

| Command | Description |
|---------|-------------|
| `make infra-bootstrap` | Create S3 state bucket |
| `make infra-init` | Initialize Terraform backend |
| `make infra-plan` | Plan changes |
| `make infra-apply` | Apply changes |
| `make infra-deploy` | Build image + push to ECR + apply |
| `make infra-destroy` | Tear down environment |
| `make infra-output` | Show Terraform outputs |
| `make infra-format` | Format `.tf` files |
| `make infra-lint` | Check formatting |
| `make infra-validate` | Validate all modules |

All commands accept `ENVIRONMENT=dev|staging|prod` and `AWS_PROFILE=your-profile`.

## Modules

| Module | Description |
|--------|-------------|
| `vpc` | VPC with public/private subnets |
| `networking` | Security groups, VPC endpoints |
| `api-gateway` | API Gateway HTTP API + Lambda (container image) |
| `container-image-repository` | ECR repository |
| `worker` | Lambda workers: document processor (EventBridge), BDA result processor (EventBridge), metrics processor (SQS), metrics aggregator (scheduled) |
| `document-data-extraction` | Bedrock Data Automation projects (multi-project, per-category routing) |
| `nosql` | DynamoDB tables (document_metadata, api_keys, tenants, audit_events, extraction_rules, document_categories, document_batches, document_builds) |
| `storage` | S3 buckets (input, output) |
| `queue` | SQS queues + DLQs (metrics pipeline) |
| `analytics` | S3 metrics bucket, Glue database with partition projection |
| `identity-provider` | Cognito User Pool (MFA optional, email verification, optional Google SSO via federated IdP) |
| `static-site` | S3 + CloudFront with OAC for admin UI and demo UI |
| `secrets` | Secrets Manager entries |
| `config` | SSM parameters, shared configuration |

## Environments

```
environments/
└── dev/
    ├── main.tf           - module composition
    ├── variables.tf      - input variable declarations
    ├── terraform.tfvars  - environment-specific values
    ├── outputs.tf        - exported values (API URL, CloudFront URL, etc.)
    └── backend.tf        - S3 state backend config
```

To add a new environment, copy `environments/dev/`, update `terraform.tfvars` (region, project name, etc.), and run `make infra-bootstrap ENVIRONMENT=<name>` to create its state bucket. You'll also need to configure Cognito callback URLs and push a container image for the new environment.

## State Management

- State stored in S3 with versioning enabled
- Bucket naming: `docai-tfstate-{account-id}-{environment}`
- Lock file based (Terraform 1.10+ `use_lockfile=true`)
- State buckets are **not** destroyed by `infra-destroy` - this is intentional

## Region

- State bucket is created in `us-east-1` (hardcoded in `infra-bootstrap`)
- Deploy region is set in `terraform.tfvars` (`region` variable) and used for all resources

## Deploy Flow

1. `infra-deploy` ensures ECR repo exists
2. Builds Docker image from `documentai-api/Dockerfile.lambda`
3. Pushes to ECR with git short SHA as tag
4. Applies all Terraform with `image_tag` variable
5. Writes `ui/admin/config.json` from Terraform outputs

Override the image tag: `make infra-deploy IMAGE_TAG=abc1234`

## Teardown

```bash
make infra-destroy ENVIRONMENT=dev
```

> **Note**: S3 buckets with objects and ECR repositories with images may block destroy. Empty them first or use `--force` flags. The state bucket is not destroyed (by design).
