# DocumentAI QA and Troubleshooting Guidance

This guide covers testing and troubleshooting DocumentAI behavior against blueprints and reference documents. It describes the standard testing workflow, diagnosing unexpected results, and maintaining the reference library.

If you're unfamiliar with the overall pipeline (preclassification, BDA (Bedrock Data Automation) blueprint matching, extraction), see the [architecture diagram](media/architecture.svg) first.

## Adding or configuring a new blueprint

Use this section whenever you:

- Add a new document type / custom blueprint under `infra/document-types/`
- Add an AWS-managed blueprint to a category's `managed_blueprints.json`
- Edit an existing custom blueprint's fields or description
- Change extraction rules, preclassification categories, or routing logic that affects which blueprint a document ends up matching

**Prerequisites** - you'll need an AWS profile with access to the shared dev account (see [SETUP.md](../../SETUP.md) and [accessing-real-aws-resources-from-docker.md](accessing-real-aws-resources-from-docker.md)), and an admin-console login with at least tenant-admin access (see [access-control.md](access-control.md)) to use the blueprint test endpoint below. 

### Step 1: Configure the blueprint

1. Add/edit the blueprint definition under `infra/document-types/<category>/`:
   - Custom blueprint: add or edit a `custom-*.json` file
   - AWS-managed blueprint: add its blueprint name to that category's `managed_blueprints.json`
   - See [infra/document-types/README.md](../../infra/document-types/README.md) for the category structure and the 40-blueprint-per-project limit.
2. If you added a new category folder, run `make -C documentai-api generate-categories` to regenerate the `PreclassificationCategory` enum from the folder names.
3. Apply the infrastructure change (`make infra-apply ENVIRONMENT=dev` from `infra/`, or the relevant Terraform workflow for your change).
4. Refresh the committed blueprint metadata so the API serves the new/changed blueprint without live BDA calls (see [2026-08-25-blueprint-schema-preload.md](../decisions/2026-08-25-blueprint-schema-preload.md)). This requires `documentai-api/.env` to exist first (`make -C documentai-api setup-env` and `make -C documentai-api env-from-aws`, if you haven't already):
   - `make -C documentai-api pull-blueprint-schemas` - regenerates `documentai-api/src/documentai_api/config/blueprint_schemas.json`
   - `make -C documentai-api pull-blueprint-fields ARN=<project-arn>` - regenerates field labels for a project, if field labels changed
   - `make -C documentai-api check-blueprint-schemas` - verifies the committed schemas file matches `infra/document-types/`, no AWS creds required; run this before opening a PR

### Step 2: Create a synthetic test document and decide what to expect

Follow ["Before you test"](#before-you-test) below: create a synthetic document (see [test-documents/README.md](../../documentai-api/tests/helpers/fixtures/test-documents/README.md) for naming/watermarking conventions - no real data, ever), and decide the expected blueprint, key fields/values, and any intentional condition under test *before* you run anything. This applies just as much to a brand-new blueprint as to troubleshooting an existing one.

### Step 3: Iterate with the blueprint test endpoint

Follow ["Executing a test"](#executing-a-test) below and use the blueprint test endpoint (`POST /v1/admin/blueprints/test` + `GET /v1/admin/blueprints/test/{test_id}`) to compare the actual matched blueprint, confidence, and extracted fields against what you decided in Step 2. Repeat until they match - only then move to Step 4. This keeps churn out of the reusable reference library described below.

### Step 4: Promote the case to automated coverage

1. Copy the synthetic document into `documentai-api/tests/helpers/fixtures/test-documents/`.
2. Add an entry for it to [`expected.json`](../../documentai-api/tests/helpers/fixtures/test-documents/expected.json) in the same folder, e.g.:

   ```json
   "synthetic-my-new-blueprint-example.jpg": {
     "bdaMatchedDocumentClass": "My-New-Blueprint",
     "content_type": "image/jpeg",
     "e2e_enabled": true,
     "isDocumentBlurry": false,
     "isPasswordProtected": false,
     "preclassificationCategory": "my_category",
     "responseCode": "000"
   }
   ```

   - Set `e2e_enabled: true` so it actually runs; use `false` only to temporarily disable a known-flaky case (see the `//` comment convention already used in that file for documenting *why*).
   - If BDA's match is known to be occasionally nondeterministic, add `reruns_override` with a comment explaining the flakiness, following the existing examples in `expected.json`.
3. If the change affects preclassification-based BDA project routing specifically, also add a case to `ROUTING_CASES` in [test_e2e_preclassification_routing.py](../../documentai-api/tests/e2e/test_e2e_preclassification_routing.py).
4. Run the e2e suite against the shared dev environment:
   - `make -C documentai-api test-e2e` - the general document-processing suite (reads `expected.json`)
   - `make -C documentai-api test-e2e-routing` - the preclassification routing suite

   Both commands regenerate `.env.e2e` from the deployed dev Terraform outputs, so there's no manual environment setup beyond AWS credentials.

[`test_app_documents.py`](../../documentai-api/tests/e2e/test_app_documents.py) is the reusable comparison mechanism: for every `expected.json` entry with `e2e_enabled: true`, it uploads the document to the real deployed API, polls until processing finishes, then asserts the DynamoDB record matches the expected outcome. For deeper field-level comparison (extracted values, confidence, missing required fields), use the blueprint test endpoint from Step 3 instead - it surfaces that detail directly rather than through DynamoDB.

### Where an AWS mock environment helps, and where it doesn't

[moto](https://docs.getmoto.org/en/latest/) mocks AWS (S3/DynamoDB/SSM) for the unit and integration tiers (`make -C documentai-api test`, `make -C documentai-api test args="-m integration"`; see [writing-tests.md](writing-tests.md#mocking-aws-services)) - useful for the plumbing around a blueprint change, but it doesn't call BDA. Blueprint match/extraction correctness always requires the e2e tier against real, deployed BDA (Steps 3-4); there's no substitute since BDA's document understanding is the thing being verified.

### Quick reference

1. Configure the blueprint under `infra/document-types/`, apply Terraform, `make -C documentai-api pull-blueprint-schemas` / `pull-blueprint-fields`, `make -C documentai-api check-blueprint-schemas`.
2. Create a synthetic document; decide the expected blueprint, fields, and any intentional condition.
3. Iterate with `POST`/`GET /v1/admin/blueprints/test` until actual matches expected.
4. Add the document + an `expected.json` entry (and a `ROUTING_CASES` entry if routing-relevant); run `make -C documentai-api test-e2e` / `make -C documentai-api test-e2e-routing`.
5. Leave the reference library (below) better than you found it.

## Before you test

1\. Use a reference or synthetic document with a known expected result  
2\. Identify the following for each document:

- Expected blueprint or document type
- Key fields and associated values
- Any intentional condition being tested (blurry document, missing field, incorrect or ambiguous document type, low-confidence extraction)

For a quick picture of what happens after a document is submitted, see the repository's [request lifecycle diagram](diagrams/request-lifecycle.mmd).

## Executing a test

1\. Execute the automated test if one exists  
2\. If the result is unexpected, run the document manually to confirm the problem is not caused by the test itself  
3\. Compare the actual response with the expected result for the reference document  

For manual testing, use the repository's [Postman collection](postman/DocumentAI.postman_collection.json).

For testing a document against a blueprint, use the blueprint test endpoint (`POST /v1/admin/blueprints/test`, admin-only; implemented in `documentai-api/src/documentai_api/app_blueprint_test.py`).

The blueprint test response can help you compare the expected and actual:

- Matched blueprint
- Blueprint confidence
- Extracted fields
- Field confidence
- Filtered fields
- Missing required fields

## Diagnosing unexpected results

| What I expected | What happened | What to check first |
| ----- | ----- | ----- |
| Document should match a known type | No expected document type matched | Confirm the document was routed and review its classification |
| Document should match Blueprint A | It matched Blueprint B | Review the BDA blueprint descriptions. The existing description may need to change, or a new blueprint may be needed |
| Document should be considered blurry | It was not flagged as blurry | Check the document's routing/configuration and the blurriness result |
| Required field should be present | Field is missing or has unexpectedly low confidence | Verify the field is defined as expected in the blueprint, then review extraction/confidence |
| Required field is intentionally absent | DocumentAI returned a value anyway | Review the extracted output and geometry (the bounding-box location BDA returns for a field on the page). A value without supporting geometry may indicate an incorrect extraction |

For an already processed document, the evaluation endpoint (`GET /v1/documents/{job_id}/evaluation`, takes an API key; implemented in `documentai-api/src/documentai_api/app_evaluation.py`) may provide a quicker explanation of which checks passed or failed before you dig into the underlying data.

## If you need to dig deeper

If the response and evaluation do not explain the discrepancy, inspect the underlying processing data in the following order:

1. Was the document routed?
2. What was its preclassification category?
3. What blueprint did BDA match?
4. What extraction and confidence values were returned?
5. Does the blueprint contain the fields you expected?
6. Does the extracted output contain geometry for the field?

> Avoid changing prompts in the code as an initial course of remediation. For classification issues, first review the BDA blueprint definition and configuration. An incorrect match may mean a change to a blueprint description or that the document warrants a separate blueprint.

### DynamoDB

DynamoDB is the starting place for investigation. The metadata table uses `fileName` as its primary key. The table also contains global secondary indexes (GSIs) on the `jobId` and `externalDocumentId` attributes. Query by `jobId` (most common), `externalDocumentId`, or `fileName`.

Depending on the case, useful attributes may include:

- Blurriness result
- Matched document class
- Preclassification category
- Missing fields
- Fields below confidence thresholds
- API response / response code

### S3

Use the stored extracted output when you need to inspect the actual extraction or field geometry. The DDB record's `bdaOutputS3Uri` attribute gives the exact path to the BDA output for a given document.

### CloudWatch

Each Lambda has structured logs in CloudWatch. Use logs when the processing path itself is unclear or you need more implementation-level detail. A CloudWatch dashboard is also available for a higher-level view of processing activity across the pipeline; see [observability.md](observability.md#cloudwatch-dashboard) for what it covers.

## Maintaining the reference library

The reference library exists to answer the question: *"For this kind of document, what should DocumentAI do?"*

Prefer cases that represent distinct behaviors or edge cases over many near-identical examples.

When QA or troubleshooting uncovers a meaningful new case:

1. Keep or create a representative synthetic/reference document
2. Record the expected blueprint and important expected fields or behavior
3. Add it to the appropriate automated QA coverage when useful
4. If the expected behavior changes intentionally, update the reference expectation

When an unfamiliar case teaches something reusable, add that learning back to the reference library or this guide

## When to stop troubleshooting

If the checks above do not explain the result:

- Review the relevant BDA documentation
- Inspect the implementation in the repository if the problem appears to be in routing or processing logic
- Ask a teammate who has context on the affected part of the pipeline
