# Document upload and processing

The platform accepts documents via API, processes them automatically, and returns structured data - extracted fields, confidence scores, and bounding box coordinates for each value found in the document.

## How a document moves through the system

When a client uploads a document, it's stored in S3 and a processing job is queued. From there, everything is event-driven - no polling, no manual steps.

A processor picks up the job and sends the document to Bedrock Data Automation, AWS's managed document intelligence service. BDA classifies the document and extracts fields using a blueprint configured for that tenant and document type. When BDA finishes, a second processor reads the results, applies any extraction rules for the tenant, and writes the final structured output to the database.

The whole pipeline runs without any human involvement. A client can upload a document and either wait for the result synchronously or check back later using the job ID.

## Blueprints

A blueprint tells BDA what to look for in a document - which fields to extract, how to identify them, and what format to expect. Each tenant can have blueprints configured for the document types they process. The platform routes each document to the right blueprint based on the category the client specifies at upload time.

For identity documents like driver's licenses and passports, the platform uses AWS Textract AnalyzeID instead of BDA, which is purpose-built for those formats.

## Supported formats

The platform accepts PDF, JPEG, PNG, and several other image formats (BMP, GIF, TIFF, WEBP, HEIC/HEIF). PDFs are limited to the first five pages. Documents must not be password-protected.

## Sync and async upload

By default, upload is asynchronous - the API returns a job ID immediately and processing happens in the background. Clients poll for the result using the job ID.

For use cases that need an immediate result, a synchronous endpoint (POST /v1/documents/wait) holds the request open until processing completes and returns the full result, subject to a configurable timeout. Note the deployed API timeout is capped by the API Gateway integration's ~30s limit - real BDA extraction commonly takes 30+ seconds (40-50s if cold-start). `/wait` can return a 503 from the gateway before processing finishes even if the job succeeds. The async upload and poll pattern doesn't have this ceiling and is what this repo's own local demo (`docs/documentai-api/api-setup-demo.tape`) uses.

## What is returned

A processed document result includes:

- The extracted fields and their values
- A confidence score for each field from the model
- Bounding box coordinates locating each value in the source image
- A status indicating whether all required fields were found

If extraction rules are configured for the tenant, only the fields allowed by those rules appear in the result. Fields the tenant doesn't need are filtered out before the result is stored.

## Local development

With the default `local.env.example` placeholders, a local upload fails immediately - the placeholder table and bucket names do not exist in AWS.

Execute `make env-from-aws` (from the `documentai-api/` directory) to connect to AWS and generate a local `.env` file. Subsequent uploads use the `.env` file, place files in S3, and trigger the deployed EventBridge pipeline. Polling the local API for the job ID returns a real `completed` status with real extracted fields.

`make env-from-aws` requires an AWS profile with dev account access, for example `AWS_PROFILE=your-profile make env-from-aws`. See [accessing-real-aws-resources-from-docker.md](accessing-real-aws-resources-from-docker.md) for details on how credentials reach the container.

See [`docs/documentai-api/api-setup-demo.tape`](api-setup-demo.tape) for a full recorded walkthrough (clone -> `make env-from-aws` -> upload -> real completion).
