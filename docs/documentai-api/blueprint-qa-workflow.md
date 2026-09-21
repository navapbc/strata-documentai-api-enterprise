# Blueprint QA Workflow

A repeatable process for adding or configuring a Bedrock Data Automation (BDA)
blueprint, proving it does what you expect with synthetic documents, and
leaving that proof behind as automated, reusable regression coverage.

This doc is the "how do I QA a blueprint change" workflow. For diagnosing an
unexpected result on an already-configured blueprint, see
[qa-and-troubleshooting.md](qa-and-troubleshooting.md).

## When to use this

Use this workflow whenever you:

- Add a new document type / custom blueprint under `infra/document-types/`
- Add an AWS-managed blueprint to a category's `managed_blueprints.json`
- Edit an existing custom blueprint's fields or description
- Change extraction rules, preclassification categories, or routing logic
  that affects which blueprint a document ends up matching

## Step 1: Add or configure the blueprint

1. Add/edit the blueprint definition under `infra/document-types/<category>/`:
   - Custom blueprint: add or edit a `custom-*.json` file
   - AWS-managed blueprint: add its blueprint name to that category's
     `managed_blueprints.json`
   - See [infra/document-types/README.md](../../infra/document-types/README.md)
     for the category structure and the 40-blueprint-per-project limit.
2. If you added a new category folder, run `make generate-categories` to
   regenerate the `PreclassificationCategory` enum from the folder names.
3. Apply the infrastructure change (`make infra-apply ENVIRONMENT=dev` from
   `infra/`, or the relevant Terraform workflow for your change).
4. Refresh the committed blueprint metadata so the API serves the new/changed
   blueprint without live BDA calls (see
   [2026-08-25-blueprint-schema-preload.md](../decisions/2026-08-25-blueprint-schema-preload.md)):
   - `make pull-blueprint-schemas` - regenerates `blueprint_schemas.json`
   - `make pull-blueprint-fields ARN=<project-arn>` - regenerates field labels
     for a project, if field labels changed
   - `make check-blueprint-schemas` - verifies the committed schemas file
     matches `infra/document-types/`, no AWS creds required; run this in CI-like
     conditions before opening a PR

## Step 2: Create a synthetic test document

1. Create or source a synthetic document that exercises the blueprint. Follow
   the conventions in
   [test-documents/README.md](../../documentai-api/tests/helpers/fixtures/test-documents/README.md):
   no real customer/applicant/employer/agency data, filename prefixed
   `synthetic-`, and watermarked or labeled as a sample.
2. Before writing anything down, decide:
   - The expected blueprint or document type
   - The key fields and their expected values
   - Any intentional condition under test (blurry scan, missing required
     field, ambiguous/incorrect document type, low-confidence extraction)

This is the same discipline described in
[qa-and-troubleshooting.md#before-you-test](qa-and-troubleshooting.md#before-you-test) -
it applies just as much to a brand-new blueprint as to troubleshooting an
existing one.

## Step 3: Iterate quickly with the blueprint test endpoint

Before committing to an automated test case, use the admin-only blueprint
test runner to confirm the blueprint behaves as expected against your
synthetic document:

- `POST /v1/admin/blueprints/test` (upload the document, get a `test_id`)
- `GET /v1/admin/blueprints/test/{test_id}` (poll for the result)

(implemented in
[blueprint_test.py](../../documentai-api/src/documentai_api/routers/blueprint_test.py);
also available via the admin console and the
[Postman collection](postman/DocumentAI.postman_collection.json)'s
"Start Blueprint Test" request)

The result gives you everything needed to compare actual vs. expected without
writing a test first:

- Matched blueprint and its confidence
- Extracted fields and per-field confidence
- Filtered fields (after extraction rules) and missing required fields

Repeat against your blueprint/document/expected-outcome until the actual
result matches what you decided in Step 2. Only then promote the case to
automated coverage - this keeps churn out of the reusable reference library.

## Step 4: Record the expected outcome and promote it to automated coverage

1. Copy the synthetic document into
   `documentai-api/tests/helpers/fixtures/test-documents/`.
2. Add an entry for it to
   [`expected.json`](../../documentai-api/tests/helpers/fixtures/test-documents/expected.json)
   in the same folder, e.g.:

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

   - Set `e2e_enabled: true` so it actually runs; use `false` only to
     temporarily disable a known-flaky case (see the `//` comment convention
     already used in that file for documenting *why*).
   - If BDA's match is known to be occasionally nondeterministic, add
     `reruns_override` with a comment explaining the flakiness, following the
     existing examples in `expected.json`.
3. If the change affects preclassification-based BDA project routing
   specifically, also add a case to `ROUTING_CASES` in
   [test_e2e_preclassification_routing.py](../../documentai-api/tests/e2e/test_e2e_preclassification_routing.py).
4. Run the e2e suite against the shared dev environment:
   - `make test-e2e` - the general document-processing suite (reads
     `expected.json`)
   - `make test-e2e-routing` - the preclassification routing suite

Both commands regenerate `.env.e2e` from the deployed dev Terraform outputs,
so there's no manual environment setup beyond AWS credentials.

## Step 5: How actual vs. expected is compared

[`test_app_documents.py`](../../documentai-api/tests/e2e/test_app_documents.py)
is the reusable comparison mechanism: for every `expected.json` entry with
`e2e_enabled: true`, it uploads the document to the real deployed API, polls
until processing finishes, then asserts the DynamoDB record matches the
expected `bdaMatchedDocumentClass`, `preclassificationCategory`,
`responseCode`, `isDocumentBlurry`, `isPasswordProtected`, and `content_type`.
For deeper field-level comparison (extracted values, confidence, missing
required fields), use the blueprint test endpoint from Step 3 - it surfaces
that detail directly rather than through DynamoDB.

## The reference library

`tests/helpers/fixtures/test-documents/` plus `expected.json` *is* the
reference library: a durable answer to "for this kind of document, what
should DocumentAI do?" Treat every blueprint addition or change as an
opportunity to leave the library better than you found it:

- Prefer one representative case per distinct behavior over many
  near-identical documents.
- If you discover an edge case while QA-ing a blueprint (ambiguous match,
  intermittent classification, a field that shouldn't be extracted), keep the
  document and record what you learned - either as an `expected.json` entry
  or, if the case doesn't fit that shape, as a note in
  [qa-and-troubleshooting.md](qa-and-troubleshooting.md).
- If expected behavior changes intentionally (e.g. a blueprint description
  change fixes a misclassification), update the corresponding `expected.json`
  entry in the same PR - don't leave the reference library describing
  behavior that's no longer intended.

## Where an AWS mock environment helps, and where it doesn't

The test suite already mocks AWS with [moto](https://docs.getmoto.org/en/latest/)
for the unit and integration tiers (see
[writing-tests.md](writing-tests.md#mocking-aws-services)). That's useful
while working on a blueprint change for the surrounding plumbing - routing
logic, S3/DynamoDB writes, error handling - without AWS credentials or
waiting on BDA: `make test` and `make test args="-m integration"`.

It does **not** help with the part this workflow exists to verify: whether
BDA actually matches the right blueprint and extracts the right fields for a
real document. BDA's document understanding is the thing under test, so
there's no substitute for running the e2e tier (Steps 3-4) against the real,
deployed BDA projects in the shared dev account. Treat moto-backed tests as a
fast pre-check for logic changes, and the e2e tier as the source of truth for
blueprint behavior.

## Quick reference

1. Configure the blueprint under `infra/document-types/`, apply Terraform,
   `make pull-blueprint-schemas` / `pull-blueprint-fields`,
   `make check-blueprint-schemas`.
2. Create a synthetic document; decide the expected blueprint, fields, and
   any intentional condition.
3. Iterate with `POST/GET /v1/admin/blueprints/test` until actual matches
   expected.
4. Add the document + an `expected.json` entry (and a `ROUTING_CASES` entry
   if routing-relevant); run `make test-e2e` / `make test-e2e-routing`.
5. Leave the reference library better than you found it.
