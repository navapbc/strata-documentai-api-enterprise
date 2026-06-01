# Test Documents

This folder contains fake, synthetic sample documents used only for testing DocumentAI
functionality, including document classification and data extraction.

These files do not contain real customer, applicant, employer, or agency data. To make
their test-only purpose clear:

- File names are prefixed with a `synthetic-` label.
- Document images are watermarked as sample documents or include the word "sample" in
  the image.

The documents are intended only to support local development, automated testing, and
demonstration workflows.

## Why synthetic documents are in this public repository

We include synthetic test documents in this public repository so users can run tests and
understand expected document-processing behavior without needing access to private data.

This approach aligns with the privacy risk reduction practices described in
[NIST SP 800-188, *De-Identifying Government Datasets: Techniques and Governance*](https://csrc.nist.gov/pubs/sp/800/188/final).
Nava Labs has evaluated disclosure risks and identified the approach outlined above as
optimal for minimizing risk when releasing de-identified or synthetic data.

## Reporting a concern

If you believe a test document contains sensitive, realistic, or inappropriate
information, please [open an issue](https://github.com/navapbc/strata-documentai-api-enterprise/issues)
so we can review and remove or replace it.
