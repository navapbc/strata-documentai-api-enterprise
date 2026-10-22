# Extraction Test Runner

The Extraction Test Runner lets you submit a document through the full pipeline and inspect the result without going through the standard ingestion flow. It's the primary tool for iterating on a blueprint before promoting a test case to automated coverage.

## See it in action

![Extraction Test Runner walkthrough](media/extraction-test-runner-walkthrough.gif)

## How it works

Select a tenant, upload a document, and click **Run Extraction**. The runner submits the document through full preclassification - the same path it would take in production. You cannot force a document category, so a misclassified document will follow the same routing it would outside of testing.

Once complete, the result shows the extracted fields and per-field confidence. If nothing matched, a status label (e.g. "No blueprint") appears in place of results.

## Recent Test Runs

Past runs appear under **Recent Test Runs** in the left panel. Clicking a run reloads its result. Runs expire after 7 days.

## When to use it

Use the Extraction Test Runner when iterating on a new or changed blueprint (see [QA and Troubleshooting](qa-and-troubleshooting.md#step-3-iterate-with-the-extraction-test-runner)). Run the document, compare the extracted fields and confidence against what you expected, adjust the blueprint definition, and repeat until the result matches before promoting the case to the automated e2e suite.
