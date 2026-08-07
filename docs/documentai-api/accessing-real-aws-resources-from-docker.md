# Accessing Real AWS Resources from Docker

`documentai-api/docker-compose.yml` mounts your local AWS credentials into the container as read-only and passes through `AWS_PROFILE`:

```yaml
services:
  documentai-api:
    volumes:
      - ~/.aws:/root/.aws:ro
    environment:
      - AWS_PROFILE
```

`.env` (copied from `local.env.example`) references `DOCUMENTAI_INPUT_LOCATION`, `DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME`, `BDA_PROJECT_ARN`, etc. The values are placeholders that do not exist in AWS. `make env-from-aws` replaces environment variables with the AWS resource names from the deployed Lambda's configuration.

## Usage

```bash
# Set your AWS profile (needs access to the dev account)
export AWS_PROFILE=your-profile-name

cd documentai-api
cp local.env.example .env   # first time only
make env-from-aws           # point .env at real dev resources
make init
make start
```

See [document-processing.md](document-processing.md#local-development) for details.

## Security Considerations

- The `:ro` flag mounts credentials as read-only for safety
- `make env-from-aws` excludes the deployed Lambda's `API_AUTH_ENABLED`, Cognito, SSM, and CORS settings; the local `local-dev-key` auth bypass remains functional
- Never commit AWS credentials to version control - `.env` is gitignored
