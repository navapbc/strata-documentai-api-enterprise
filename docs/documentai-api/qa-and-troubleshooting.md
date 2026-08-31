# DocumentAI QA and Troubleshooting Guidance

This guide covers testing and troubleshooting DocumentAI behavior against blueprints and reference documents. It describes the standard testing workflow, diagnosing unexpected results, and maintaining the reference library.

If you're unfamiliar with the overall pipeline (preclassification, BDA blueprint matching, extraction), see the [architecture diagram](media/architecture.svg) first.

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
